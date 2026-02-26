"""TOOL_ROWS：由 data/tools/* 各模块组成，供 init_db 使用。"""

from app.dao.data.tools.tool_01_demo_tool import ROW as _row_tool_01_demo_tool
from app.dao.data.tools.tool_02_tool_list_data_source import (
    ROW as _row_tool_02_tool_list_data_source,
)
from app.dao.data.tools.tool_03_tool_create_data_source import (
    ROW as _row_tool_03_tool_create_data_source,
)
from app.dao.data.tools.tool_04_tool_get_data_source import ROW as _row_tool_04_tool_get_data_source
from app.dao.data.tools.tool_05_tool_update_data_source import (
    ROW as _row_tool_05_tool_update_data_source,
)
from app.dao.data.tools.tool_06_tool_delete_data_source import (
    ROW as _row_tool_06_tool_delete_data_source,
)
from app.dao.data.tools.tool_07_tool_test_data_source import (
    ROW as _row_tool_07_tool_test_data_source,
)
from app.dao.data.tools.tool_08_tool_execute_sql_data_source import (
    ROW as _row_tool_08_tool_execute_sql_data_source,
)
from app.dao.data.tools.tool_09_tool_list_data_models_by_data_source import (
    ROW as _row_tool_09_tool_list_data_models_by_data_source,
)
from app.dao.data.tools.tool_10_tool_delete_data_models_by_data_source import (
    ROW as _row_tool_10_tool_delete_data_models_by_data_source,
)
from app.dao.data.tools.tool_11_tool_import_data_models_by_data_source import (
    ROW as _row_tool_11_tool_import_data_models_by_data_source,
)
from app.dao.data.tools.tool_12_tool_get_data_model import ROW as _row_tool_12_tool_get_data_model
from app.dao.data.tools.tool_13_tool_delete_data_model import (
    ROW as _row_tool_13_tool_delete_data_model,
)
from app.dao.data.tools.tool_14_tool_update_data_model_semantic_and_summary import (
    ROW as _row_tool_14_tool_update_data_model_semantic_and_summary,
)
from app.dao.data.tools.tool_15_tool_get_data_models_semantic import (
    ROW as _row_tool_15_tool_get_data_models_semantic,
)
from app.dao.data.tools.tool_16_tool_execute_sql_data_model import (
    ROW as _row_tool_16_tool_execute_sql_data_model,
)
from app.dao.data.tools.tool_17_tool_check_data_sources_basic_info import (
    ROW as _row_tool_17_tool_check_data_sources_basic_info,
)
from app.dao.data.tools.tool_18_tool_check_data_source_connection import (
    ROW as _row_tool_18_tool_check_data_source_connection,
)
from app.dao.data.tools.tool_19_tool_check_data_source_has_models import (
    ROW as _row_tool_19_tool_check_data_source_has_models,
)
from app.dao.data.tools.tool_20_tool_check_models_exist_in_database import (
    ROW as _row_tool_20_tool_check_models_exist_in_database,
)
from app.dao.data.tools.tool_21_tool_check_models_semantic import (
    ROW as _row_tool_21_tool_check_models_semantic,
)
from app.dao.data.tools.tool_22_tool_check_semantic_freshness import (
    ROW as _row_tool_22_tool_check_semantic_freshness,
)

TOOL_ROWS = [
    _row_tool_01_demo_tool,
    _row_tool_02_tool_list_data_source,
    _row_tool_03_tool_create_data_source,
    _row_tool_04_tool_get_data_source,
    _row_tool_05_tool_update_data_source,
    _row_tool_06_tool_delete_data_source,
    _row_tool_07_tool_test_data_source,
    _row_tool_08_tool_execute_sql_data_source,
    _row_tool_09_tool_list_data_models_by_data_source,
    _row_tool_10_tool_delete_data_models_by_data_source,
    _row_tool_11_tool_import_data_models_by_data_source,
    _row_tool_12_tool_get_data_model,
    _row_tool_13_tool_delete_data_model,
    _row_tool_14_tool_update_data_model_semantic_and_summary,
    _row_tool_15_tool_get_data_models_semantic,
    _row_tool_16_tool_execute_sql_data_model,
    _row_tool_17_tool_check_data_sources_basic_info,
    _row_tool_18_tool_check_data_source_connection,
    _row_tool_19_tool_check_data_source_has_models,
    _row_tool_20_tool_check_models_exist_in_database,
    _row_tool_21_tool_check_models_semantic,
    _row_tool_22_tool_check_semantic_freshness,
]
