from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.app.models.user import User


class PermissionService:
    @staticmethod
    def get_full_geo_scope(user: User):
        """Returns all geographical tags associated with the user."""
        return {
            "territory_id": getattr(user, 'assigned_territory_id', None),
            "area_id": getattr(user, 'assigned_area_id', None),
            "region_id": getattr(user, 'assigned_region_id', None),
            "state_id": getattr(user, 'assigned_state_id', None),
            "zone_id": getattr(user, 'assigned_zone_id', None)
        }

    @staticmethod
    def apply_geo_filter(query, model, user: User):
        """
        Dynamically applies the most granular geographic filter possible.
        Prevents upward blindness and data leaks.
        """
        scope = PermissionService.get_full_geo_scope(user)

        geo_columns = ["territory_id", "area_id", "region_id", "state_id", "zone_id"]

        for geo_col in geo_columns:
            if hasattr(model, geo_col) and scope.get(geo_col) is not None:
                return query.filter(getattr(model, geo_col) == scope[geo_col])
        return query.filter(model.id == -1)

    @staticmethod
    def get_geo_scope(user: User):
        """Legacy fallback for endpoints doing manual dict unpacking (**scope)"""
        scope = PermissionService.get_full_geo_scope(user)
        return {k: v for k, v in scope.items() if v is not None}

    @staticmethod
    def verify_internal_jurisdiction(db: Session, current_user: User, entity_model, entity_id: int):
        """
        CRITICAL SECURITY: Verifies if an internal user has geographical jurisdiction over a specific partner.
        Prevents cross-territory spoofing by ZSMs, ASMs, SOs.
        """
        user_perms = [p.name for p in current_user.role.permissions] if current_user.role else []
        if "manage_roles" in user_perms:
            return True  # Super Admins bypass jurisdiction checks

        # Apply the Smart Cascade filter to the requested entity
        query = db.query(entity_model).filter(entity_model.id == entity_id)
        query = PermissionService.apply_geo_filter(query, entity_model, current_user)

        if not query.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Jurisdiction Denied: This entity is outside your assigned geographical territory."
            )