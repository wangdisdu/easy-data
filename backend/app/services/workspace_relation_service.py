"""
工作空间关系服务层
"""

import time

from sqlalchemy.orm import Session

from app.dao.models import TbWorkSpaceRelation


class WorkSpaceRelationService:
    """工作空间关系服务"""

    @staticmethod
    def set_resource_workspaces(
        db: Session, resource_type: str, resource_id: int, workspace_ids: list[int]
    ) -> list[TbWorkSpaceRelation]:
        """
        设置资源的关联工作空间

        Args:
            db: 数据库会话
            resource_type: 资源类型(data_source, data_model等)
            resource_id: 资源ID
            workspace_ids: 工作空间ID列表

        Returns:
            创建的关系列表
        """
        # 删除原有的关系
        db.query(TbWorkSpaceRelation).filter(
            TbWorkSpaceRelation.resource_type == resource_type,
            TbWorkSpaceRelation.resource_id == resource_id,
        ).delete()

        # 创建新的关系
        current_time = int(time.time() * 1000)
        relations = []
        for ws_id in workspace_ids:
            relation = TbWorkSpaceRelation(
                ws_id=ws_id,
                resource_type=resource_type,
                resource_id=resource_id,
                create_time=current_time,
                update_time=current_time,
            )
            db.add(relation)
            relations.append(relation)

        db.commit()
        return relations

    @staticmethod
    def get_resource_workspaces(db: Session, resource_type: str, resource_id: int) -> list[int]:
        """
        获取资源关联的工作空间ID列表

        Args:
            db: 数据库会话
            resource_type: 资源类型
            resource_id: 资源ID

        Returns:
            工作空间ID列表
        """
        relations = (
            db.query(TbWorkSpaceRelation)
            .filter(
                TbWorkSpaceRelation.resource_type == resource_type,
                TbWorkSpaceRelation.resource_id == resource_id,
            )
            .all()
        )
        return [relation.ws_id for relation in relations]

    @staticmethod
    def get_workspace_resources(db: Session, ws_id: int, resource_type: str) -> list[int]:
        """
        获取工作空间关联的资源ID列表

        Args:
            db: 数据库会话
            ws_id: 工作空间ID
            resource_type: 资源类型

        Returns:
            资源ID列表
        """
        relations = (
            db.query(TbWorkSpaceRelation)
            .filter(
                TbWorkSpaceRelation.ws_id == ws_id,
                TbWorkSpaceRelation.resource_type == resource_type,
            )
            .all()
        )
        return [relation.resource_id for relation in relations]

    @staticmethod
    def delete_resource_relations(db: Session, resource_type: str, resource_id: int):
        """
        删除资源的所有关系

        Args:
            db: 数据库会话
            resource_type: 资源类型
            resource_id: 资源ID
        """
        db.query(TbWorkSpaceRelation).filter(
            TbWorkSpaceRelation.resource_type == resource_type,
            TbWorkSpaceRelation.resource_id == resource_id,
        ).delete()
        db.commit()
