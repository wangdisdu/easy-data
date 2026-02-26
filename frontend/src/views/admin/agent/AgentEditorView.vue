<template>
  <div class="agent-editor">
    <!-- 顶部工具栏 -->
    <div class="editor-header">
      <div class="header-left">
        <a-button type="link" @click="handleBack">
          <ArrowLeftOutlined />
          返回
        </a-button>
        <a-divider type="vertical" />
        <span class="agent-name">{{ agentName || '' }}</span>
      </div>
      <div class="header-right">
        <a-button @click="handleSave" type="primary" :loading="saving">
          <SaveOutlined />
          保存
        </a-button>
      </div>
    </div>

    <!-- 左中右布局 -->
    <div class="editor-content">
      <!-- 左侧：节点选择面板 -->
      <div class="editor-left">
        <div class="node-palette">
          <div
            v-for="nodeType in nodeTypes"
            :key="nodeType.type"
            class="node-item"
            :draggable="true"
            @dragstart="handleDragStart($event, nodeType)"
          >
            <div class="node-icon" :class="`node-${nodeType.type}`">
              <img :src="nodeType.icon" :alt="nodeType.label" />
            </div>
            <div class="node-label">{{ nodeType.label }}</div>
          </div>
        </div>
      </div>

      <!-- 中间：DAG图形编辑区域 -->
      <div class="editor-center">
        <div ref="graphContainer" class="graph-container" @drop="handleDrop" @dragover.prevent></div>
      </div>

      <!-- 右侧：节点配置面板 -->
      <div class="editor-right">
        <div v-if="selectedNode" class="config-panel">
          <div class="config-panel-title">
            <img :src="getNodeIconSvg(selectedNode.node_type)" :alt="getNodeTypeLabel(selectedNode.node_type)" class="card-title-icon" />
            <span>{{ rightPanelTitle }}</span>
          </div>
          <a-form :model="nodeConfig" layout="vertical">
            <!-- 通用配置 -->
            <a-form-item label="节点名称">
              <a-input v-model:value="nodeConfig.name" placeholder="请输入节点名称" />
            </a-form-item>
            <a-form-item label="描述">
              <a-textarea v-model:value="nodeConfig.description" :rows="3" placeholder="请输入节点描述" />
            </a-form-item>

            <!-- LLM节点配置 -->
            <template v-if="selectedNode.node_type === 'llm'">
              <a-form-item label="LLM模型" name="llm_id">
                <a-select
                  v-model:value="nodeConfig.llm_id"
                  placeholder="请选择LLM模型"
                  :options="llmOptions"
                  show-search
                  :filter-option="filterOption"
                />
              </a-form-item>
              <a-form-item label="脚本 (script)">
                <a-textarea v-model:value="nodeConfig.script" :rows="6" placeholder="请输入脚本" />
              </a-form-item>
              <a-form-item label="工具选择（可多选）">
                <a-select
                  v-model:value="nodeConfig.tool_ids"
                  mode="multiple"
                  placeholder="请选择工具"
                  :options="toolOptions"
                  show-search
                  :filter-option="filterOption"
                />
              </a-form-item>
            </template>

            <!-- Tool节点配置 -->
            <template v-if="selectedNode.node_type === 'tool'">
              <a-form-item label="工具选择（可多选）" name="tool_ids">
                <a-select
                  v-model:value="nodeConfig.tool_ids"
                  mode="multiple"
                  placeholder="请选择工具"
                  :options="toolOptions"
                  show-search
                  :filter-option="filterOption"
                />
              </a-form-item>
            </template>

            <!-- Subgraph节点配置 -->
            <template v-if="selectedNode.node_type === 'subgraph'">
              <a-form-item label="子图智能体" name="subgraph_agent_id">
                <a-select
                  v-model:value="nodeConfig.subgraph_agent_id"
                  placeholder="请选择智能体"
                  :options="agentOptions"
                  show-search
                  :filter-option="filterOption"
                />
              </a-form-item>
            </template>

            <!-- Python节点配置 -->
            <template v-if="selectedNode.node_type === 'python'">
              <a-form-item label="脚本 (script)">
                <a-textarea
                  v-model:value="nodeConfig.script"
                  :rows="10"
                  placeholder="请输入脚本"
                />
              </a-form-item>
            </template>

            <!-- Condition节点配置 -->
            <template v-if="selectedNode.node_type === 'condition'">
              <a-form-item label="脚本 (script)">
                <a-textarea v-model:value="nodeConfig.script" :rows="6" placeholder="请输入脚本" />
              </a-form-item>
              <a-form-item label="路由映射">
                <div
                  v-for="(text, idx) in nodeConfig.route_mapping_texts"
                  :key="idx"
                  class="route-mapping-item"
                >
                  <a-input v-model:value="nodeConfig.route_mapping_texts[idx]" placeholder="请输入路由映射文本" />
                  <a-button type="link" danger @click="removeRouteMappingText(idx)">移除</a-button>
                </div>
                <a-button block @click="addRouteMappingText">新增路由</a-button>
              </a-form-item>
            </template>

            <a-form-item>
              <a-button type="primary" block @click="handleUpdateNodeConfig">确定</a-button>
            </a-form-item>
          </a-form>
        </div>
        <a-empty v-else description="请选择一个节点进行配置" class="config-empty" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  ApiOutlined,
  ToolOutlined,
  CodeOutlined,
  BranchesOutlined,
  RobotOutlined,
} from '@ant-design/icons-vue'
import { Graph, Shape } from '@antv/x6'
import { getAgent, getAgentGraph, saveAgentGraph } from '@/api/agent'
import { getLlms } from '@/api/llm'
import { getTools } from '@/api/tool'
import { getAgents } from '@/api/agent'
import type {
  AgentGraphNode,
  AgentGraphEdge,
  LlmNodeConfig,
  ConditionNodeConfig,
  ToolNodeConfig,
  PythonNodeConfig,
  SubgraphNodeConfig
} from '@/api/agent'
import nodeStartSvg from '@/assets/node_start.svg'
import nodeEndSvg from '@/assets/node_end.svg'
import nodeLlmSvg from '@/assets/node_llm.svg'
import nodeToolSvg from '@/assets/node_tool.svg'
import nodePythonSvg from '@/assets/node_python.svg'
import nodeSubgraphSvg from '@/assets/node_subgraph.svg'
import nodeConditionSvg from '@/assets/node_condition.svg'

/**
 * 智能体图编辑器：左侧节点类型拖拽、中间 X6 DAG、右侧节点配置。
 * 数据流：nodeMap 与画布同步，保存时从 nodeMap + 画布边 组装 AgentGraphModel 请求。
 */

// ========== 路由与状态 ==========

const route = useRoute()
const router = useRouter()

/** 从路由解析当前智能体 id，新建页为 null */
const getAgentId = (): number | null => {
  if (route.name === 'admin-agent-new') return null
  if (route.params.id && route.params.id !== 'new') {
    const id = Number(route.params.id)
    return isNaN(id) ? null : id
  }
  return null
}

const agentId = ref<number | null>(getAgentId())
const agentName = ref<string>('')
const saving = ref(false)
const graphContainer = ref<HTMLDivElement>()
const graph = ref<Graph | null>(null)
const selectedNode = ref<AgentGraphNode | null>(null)
/** 画布节点 id(string) -> 节点数据，与 Graph 节点同步，保存时由此组装请求体 */
const nodeMap = ref<Map<string, AgentGraphNode>>(new Map())
/** 新建节点临时 id，从 -1 递减，避免与后端返回的正数 id 冲突 */
const nextNewId = ref(-1)

// ========== 常量与配置 ==========

/** 节点类型：左侧面板与节点图标、标签的配置 */
const nodeTypes = [
  { type: 'start', label: '起始点', icon: nodeStartSvg },
  { type: 'end', label: '结束点', icon: nodeEndSvg },
  { type: 'llm', label: '大模型节点', icon: nodeLlmSvg },
  { type: 'tool', label: '工具节点', icon: nodeToolSvg },
  { type: 'python', label: '处理节点', icon: nodePythonSvg },
  { type: 'subgraph', label: '子图节点', icon: nodeSubgraphSvg },
  { type: 'condition', label: '条件分支', icon: nodeConditionSvg },
]

/** 右侧配置表单绑定，随 selectedNode 由 loadNodeConfig 填入，由 flushSelectedNodeConfig 写回 nodeMap */
const nodeConfig = reactive({
  name: '',
  description: '',
  llm_id: undefined as number | undefined,
  tool_ids: [] as number[],
  subgraph_agent_id: undefined as number | undefined,
  script: '',
  route_mapping_texts: [] as string[],
})

const llmOptions = ref<Array<{ label: string; value: number }>>([])
const toolOptions = ref<Array<{ label: string; value: number }>>([])
const agentOptions = ref<Array<{ label: string; value: number }>>([])

// ========== 工具函数 ==========

const getNodeTypeLabel = (nodeType: string): string =>
  nodeTypes.find((n) => n.type === nodeType)?.label ?? nodeType

/** 获取节点类型对应的 SVG 图标路径 */
const getNodeIconSvg = (nodeType: string): string => {
  const map: Record<string, string> = {
    start: nodeStartSvg,
    end: nodeEndSvg,
    llm: nodeLlmSvg,
    tool: nodeToolSvg,
    python: nodePythonSvg,
    subgraph: nodeSubgraphSvg,
    condition: nodeConditionSvg,
  }
  return map[nodeType] ?? nodeStartSvg
}


/** 输出槽位 slot(0,1,2…) ↔ 右侧 port id；from_node_slot 对应 source.port */
const getOutputPortIdBySlot = (slot: number) =>
  (slot == null || slot <= 0) ? 'port-output' : `port-output-${slot}`
const getSlotByOutputPortId = (portId?: string | null): number => {
  if (!portId || portId === 'port-output') return 0
  const m = /^port-output-(\d+)$/.exec(portId)
  return m ? Number(m[1]) : 0
}

/** 输入槽位 slot(0,1,2…) ↔ 左侧 port id；to_node_slot 对应 target.port */
const getInputPortIdBySlot = (slot: number) =>
  (slot == null || slot <= 0) ? 'port-input' : `port-input-${slot}`
const getSlotByInputPortId = (portId?: string | null): number => {
  if (!portId || portId === 'port-input') return 0
  const m = /^port-input-(\d+)$/.exec(portId)
  return m ? Number(m[1]) : 0
}

/** 从节点 config.route_mapping 取长度，作为条件节点的输出 slot 数量 */
function getRouteCountFromConfig(configJson: string | undefined): number {
  if (!configJson) return 1
  try {
    const config = JSON.parse(configJson) as ConditionNodeConfig
    return Array.isArray(config.route_mapping) && config.route_mapping.length > 0 ? config.route_mapping.length : 1
  } catch {
    return 1
  }
}

/** 条件节点：按 route_mapping 数量设置 1 个输入 slot（左）+ N 个输出 slot（右）。减少 port 时需 rewrite: true 才能正确触发视图更新。 */
const syncConditionNodePorts = (nodeIdStr: string, outputSlotCount: number) => {
  if (!graph.value) return
  const cell = graph.value.getCellById(nodeIdStr)
  if (!cell?.isNode()) return
  const n = Math.max(1, outputSlotCount || 0)
  const items = [{ id: 'port-input', group: 'input' }]
  for (let i = 0; i < n; i++) {
    items.push({ id: getOutputPortIdBySlot(i), group: 'output' })
  }
  cell.setPropByPath('ports/items', items, { rewrite: true })
}

/** 按节点类型设置输入/输出 slot 对应的 port：start 仅输出，end 仅输入，condition 多输出，其它 1 入 1 出 */
const applyPortsForNode = (nodeIdStr: string, nodeType: string, conditionOutputSlotCount?: number) => {
  if (!graph.value) return
  const cell = graph.value.getCellById(nodeIdStr)
  if (!cell?.isNode()) return
  if (nodeType === 'start') {
    cell.setPropByPath('ports/items', [{ id: 'port-output', group: 'output' }])
    return
  }
  if (nodeType === 'end') {
    cell.setPropByPath('ports/items', [{ id: 'port-input', group: 'input' }])
    return
  }
  if (nodeType === 'condition') {
    syncConditionNodePorts(nodeIdStr, conditionOutputSlotCount ?? 1)
    return
  }
  cell.setPropByPath('ports/items', [
    { id: 'port-input', group: 'input' },
    { id: 'port-output', group: 'output' },
  ])
}

const rightPanelTitle = computed(() =>
  selectedNode.value ? getNodeTypeLabel(selectedNode.value.node_type) : '节点配置'
)

// ========== 图初始化 ==========

/**
 * 初始化 X6 画布：注册节点/边形状、创建 Graph、绑定事件。
 * 若有 agentId 则 onMounted 内会调 loadAgentData 拉取并渲染。
 */
const initGraph = () => {
  if (!graphContainer.value) return

  // 注册节点：矩形 + 图标 + 文案；左 port=输入 slot，右 port=输出 slot，具体由 applyPortsForNode 按类型设置
  Shape.Rect.registry.register(
    'agent-graph-node',
    {
      inherit: 'rect',
      width: 120,
      height: 60,
      markup: [
        { tagName: 'rect', selector: 'body' },
        { tagName: 'image', selector: 'icon' },
        { tagName: 'text', selector: 'label' },
      ],
      attrs: {
        body: {
          strokeWidth: 1,
          stroke: '#5F95FF',
          fill: '#e6f7ff',
          rx: 6,
          ry: 6,
        },
        icon: {
          width: 16,
          height: 16,
          refX: '50%',
          refY: '35%',
          refX2: -12,
          refY2: -12,
        },
        label: {
          fontSize: 12,
          fill: '#262626',
          refX: '50%',
          refY: '65%',
          textAnchor: 'middle',
          textVerticalAnchor: 'middle',
        },
      },
      // 端口：input=左侧=输入 slot，output=右侧=输出 slot；items 按节点类型在 applyPortsForNode 中设置
      ports: {
        groups: {
          input: { position: 'left', attrs: { circle: { r: 4, magnet: true, stroke: '#5F95FF', strokeWidth: 1, fill: '#5F95FF' } } },
          output: { position: 'right', attrs: { circle: { r: 4, magnet: true, stroke: '#5F95FF', strokeWidth: 1, fill: '#5F95FF' } } },
        },
        items: [],
      },
    },
    true
  )

  // 注册边：source.port=源节点输出 slot 对应 port，target.port=目标节点输入 slot 对应 port
  Shape.Edge.registry.register(
    'agent-graph-edge',
    {
      inherit: 'edge',
      attrs: {
        line: {
          stroke: '#5F95FF',
          strokeWidth: 1,
          targetMarker: {
            name: 'block',
            width: 12,
            height: 8,
          },
        },
      },
    },
    true
  )

  graph.value = new Graph({
    container: graphContainer.value,
    grid: {
      visible: true,
      type: 'dot',
      args: {
        color: '#e0e0e0',
        thickness: 1,
      },
    },
    panning: {
      enabled: true,
      eventTypes: ['leftMouseDown', 'mouseWheel'],
    },
    mousewheel: {
      enabled: true,
      zoomAtMousePosition: true,
      modifiers: 'ctrl',
      minScale: 0.5,
      maxScale: 3,
    },
    connecting: {
      router: 'manhattan',
      connector: {
        name: 'rounded',
        args: {
          radius: 8,
        },
      },
      anchor: 'center',
      connectionPoint: 'anchor',
      allowBlank: false,
      snap: {
        radius: 20,
      },
      createEdge() {
        return graph.value!.createEdge({
          shape: 'agent-graph-edge',
        })
      },
      validateConnection({ targetMagnet }) {
        return !!targetMagnet
      },
    },
    highlighting: {
      magnetAdsorbed: {
        name: 'stroke',
        args: {
          attrs: {
            fill: '#5F95FF',
            stroke: '#5F95FF',
          },
        },
      },
    },
    selecting: {
      enabled: true,
      rubberband: true,
      showNodeSelectionBox: true,
    },
    snapline: {
      enabled: true,
    },
  })

  // --- 节点事件 ---
  /** 节点：鼠标移入时在节点右上角显示删除按钮（button-remove） */
  graph.value.on('node:mouseenter', ({ node }) => {
    node.addTools({
      name: 'button-remove',
      args: {
        x: '100%',
        y: 0,
        offset: { x: -8, y: 8 },
      },
    })
  })

  /** 节点：鼠标移出时移除该节点上的 tools（收起删除按钮） */
  graph.value.on('node:mouseleave', ({ node }) => {
    node.removeTools()
  })

  /** 节点：点击节点上的 tool 时触发；若为删除按钮则从画布与 nodeMap 中移除该节点 */
  graph.value.on('node:tool:click', ({ tool, node }) => {
    if (tool.name === 'button-remove') handleDeleteNode(node.id as string)
  })

  /** 节点：单击时将该节点数据加载到右侧配置面板（nodeConfig），并应用选中高亮效果 */
  graph.value.on('node:click', ({ node }) => {
    const nodeId = node.id as string
    loadNodeConfig(nodeId)

    // 清除所有节点的选中样式
    graph.value!.getNodes().forEach((n) => {
      n.attr('body/filter', false)
    })

    // 为当前点击的节点应用选中样式
    node.attr('body/filter', {
      name: 'dropShadow',
      args: {
        dx: 0,
        dy: 2,
        blur: 8,
        color: '#1890ff',
      },
    })
  })

  /** 节点：双击时同样打开右侧配置（与单击一致） */
  graph.value.on('node:dblclick', ({ node }) => loadNodeConfig(node.id as string))

  // --- 边事件 ---
  /** 边：鼠标移入时在边上显示删除按钮 */
  graph.value.on('edge:mouseenter', ({ edge }) => {
    edge.addTools({
      name: 'button-remove',
      args: {
        distance: -40,
      },
    })
  })

  /** 边：鼠标移出时移除该边上的 tools（收起删除按钮） */
  graph.value.on('edge:mouseleave', ({ edge }) => {
    edge.removeTools()
  })

  /** 边：点击边上的删除按钮时从画布移除该边 */
  graph.value.on('edge:tool:click', ({ tool, edge }) => {
    if (tool.name === 'button-remove') handleDeleteEdge(edge.id as string)
  })

  // --- 画布事件 ---
  /** 画布空白：点击空白区域时取消当前选中节点，清空右侧配置面板，并清除所有节点的选中样式 */
  graph.value.on('blank:click', () => {
    selectedNode.value = null
    // 清除所有节点的选中样式
    graph.value!.getNodes().forEach((node) => {
      node.attr('body/filter', false)
    })
  })

  if (agentId.value && agentId.value > 0) loadAgentData()
}

// ========== 节点与配置 ==========

/** 从左侧拖拽到画布时写入 dataTransfer，在 handleDrop 中读取 */
const handleDragStart = (e: DragEvent, nodeType: (typeof nodeTypes)[number]) => {
  e.dataTransfer!.effectAllowed = 'move'
  e.dataTransfer!.setData('nodeType', nodeType.type)
  e.dataTransfer!.setData('nodeLabel', nodeType.label)
}

/** 画布 drop：根据 dataTransfer 创建节点并加入 nodeMap */
const handleDrop = (e: DragEvent) => {
  if (!graph.value) return
  e.preventDefault()
  const nodeType = e.dataTransfer!.getData('nodeType')
  const nodeLabel = e.dataTransfer!.getData('nodeLabel')
  if (!nodeType) return
  const point = graph.value.clientToLocal(e.clientX, e.clientY)
  createNodeOnGraph(nodeType, nodeLabel, point.x, point.y)
}

/** 在画布指定位置添加节点，id 使用 nextNewId 递减；同时写入 nodeMap 供保存使用 */
const createNodeOnGraph = (nodeType: string, nodeLabel: string, x: number, y: number) => {
  if (!graph.value) return

  const id = nextNewId.value
  nextNewId.value -= 1
  const nodeId = String(id)

  const iconSvg = getNodeIconSvg(nodeType)

  graph.value.addNode({
    id: nodeId,
    shape: 'agent-graph-node',
    x,
    y,
    attrs: {
      icon: { xlinkHref: iconSvg },
      label: { text: nodeLabel },
    },
    data: { node_type: nodeType },
  })

  nodeMap.value.set(nodeId, {
    id,
    name: nodeLabel,
    node_type: nodeType,
    description: '',
    config: '',
  })

  applyPortsForNode(nodeId, nodeType, nodeType === 'condition' ? 1 : undefined)
}

/** 点击节点时：从 nodeMap 取出数据填到 nodeConfig；不修改画布上的 port（条件节点的 port 仅在「更新配置」后生效） */
const loadNodeConfig = (nodeIdStr: string) => {
  if (!graph.value) return
  const node = nodeMap.value.get(nodeIdStr)
  if (!node) return
  selectedNode.value = node

  try {
    const parsedConfig = node.config ? JSON.parse(node.config) : {}

    // 根据节点类型解析配置
    if (node.node_type === 'llm') {
      const config = parsedConfig as LlmNodeConfig
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: config.llm_id,
        tool_ids: config.tool_ids ?? [],
        subgraph_agent_id: undefined,
        script: config.script || '',
        route_mapping_texts: [''],
      })
    } else if (node.node_type === 'tool') {
      const config = parsedConfig as ToolNodeConfig
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: undefined,
        tool_ids: config.tool_ids ?? [],
        subgraph_agent_id: undefined,
        script: '',
        route_mapping_texts: [''],
      })
    } else if (node.node_type === 'subgraph') {
      const config = parsedConfig as SubgraphNodeConfig
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: undefined,
        tool_ids: [],
        subgraph_agent_id: config.agent_id,  // 后端 Model 使用 agent_id，前端使用 subgraph_agent_id
        script: '',
        route_mapping_texts: [''],
      })
    } else if (node.node_type === 'python') {
      const config = parsedConfig as PythonNodeConfig
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: undefined,
        tool_ids: [],
        subgraph_agent_id: undefined,
        script: config.script || '',
        route_mapping_texts: [''],
      })
    } else if (node.node_type === 'condition') {
      const config = parsedConfig as ConditionNodeConfig
      const routeMappingTexts: string[] = Array.isArray(config.route_mapping)
        ? config.route_mapping.map((it: unknown) => String(it))
        : ['']
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: undefined,
        tool_ids: [],
        subgraph_agent_id: undefined,
        script: config.script || '',
        route_mapping_texts: routeMappingTexts.length ? routeMappingTexts : [''],
      })
    } else {
      // start/end 节点没有配置
      Object.assign(nodeConfig, {
        name: node.name || getNodeTypeLabel(node.node_type),
        description: node.description || '',
        llm_id: undefined,
        tool_ids: [],
        subgraph_agent_id: undefined,
        script: '',
        route_mapping_texts: [''],
      })
    }
  } catch (e) {
    console.error('解析节点配置失败', e)
    // 解析失败时使用默认值
    Object.assign(nodeConfig, {
      name: node.name || getNodeTypeLabel(node.node_type),
      description: node.description || '',
      llm_id: undefined,
      tool_ids: [],
      subgraph_agent_id: undefined,
      script: '',
      route_mapping_texts: [''],
    })
  }
}

/** 条件节点：新增一行路由；仅改表单，不更新画布 port，需点「更新配置」后 port 才生效 */
const addRouteMappingText = () => {
  nodeConfig.route_mapping_texts.push('')
}

/** 条件节点：删除一行路由，至少保留一行；仅改表单，不更新画布 port，需点「更新配置」后 port 才生效 */
const removeRouteMappingText = (idx: number) => {
  nodeConfig.route_mapping_texts.splice(idx, 1)
  if (nodeConfig.route_mapping_texts.length === 0) nodeConfig.route_mapping_texts.push('')
}

/** 把右侧表单 nodeConfig 写回 nodeMap 中当前选中节点，刷新画布 label，条件节点在此处同步输出 port 数；保存前、点「更新配置」时调用 */
const flushSelectedNodeConfig = () => {
  if (!selectedNode.value || !graph.value) return
  const key = String(selectedNode.value.id)
  const node = nodeMap.value.get(key)
  if (!node) return

  let config: LlmNodeConfig | ConditionNodeConfig | ToolNodeConfig | PythonNodeConfig | SubgraphNodeConfig | null = null

  if (selectedNode.value.node_type === 'llm') {
    const llmConfig: LlmNodeConfig = {
      llm_id: nodeConfig.llm_id!,
      script: nodeConfig.script ?? '',
      tool_ids: nodeConfig.tool_ids ?? [],
    }
    config = llmConfig
  } else if (selectedNode.value.node_type === 'tool') {
    const toolConfig: ToolNodeConfig = {
      tool_ids: nodeConfig.tool_ids ?? [],
    }
    config = toolConfig
  } else if (selectedNode.value.node_type === 'subgraph') {
    const subgraphConfig: SubgraphNodeConfig = {
      agent_id: nodeConfig.subgraph_agent_id!,  // 前端使用 subgraph_agent_id，后端 Model 使用 agent_id
    }
    config = subgraphConfig
  } else if (selectedNode.value.node_type === 'python') {
    const pythonConfig: PythonNodeConfig = {
      script: nodeConfig.script ?? '',
    }
    config = pythonConfig
  } else if (selectedNode.value.node_type === 'condition') {
    const texts = (nodeConfig.route_mapping_texts ?? []).map((t) => String(t ?? '').trim())
    const conditionConfig: ConditionNodeConfig = {
      script: nodeConfig.script ?? '',
      route_mapping: texts.length ? texts : [''],
    }
    config = conditionConfig
  }

  node.name = nodeConfig.name || getNodeTypeLabel(node.node_type)
  node.description = nodeConfig.description ?? ''
  node.config = config ? JSON.stringify(config) : ''

  nodeMap.value.set(key, node)

  const cell = graph.value.getCellById(key)
  if (cell?.isNode()) {
    cell.setAttrs({ label: { text: node.name || '' } })
    if (selectedNode.value.node_type === 'condition' && config && 'route_mapping' in config) {
      const n = Array.isArray(config.route_mapping) ? config.route_mapping.length : 1
      syncConditionNodePorts(key, n)
    }
  }
}

const handleUpdateNodeConfig = () => {
  try {
    flushSelectedNodeConfig()
    message.success('配置已更新（请点击保存按钮保存到数据库）')
  } catch {
    message.error('更新配置失败')
  }
}

// ========== 数据加载与保存 ==========

/** 拉取智能体名称与图数据，清空画布后按 nodes/edges 渲染，并填满 nodeMap */
const loadAgentData = async () => {
  if (!agentId.value) return

  try {
    const agentRes = await getAgent(agentId.value)
    agentName.value = agentRes.data.name

    const graphRes = await getAgentGraph(agentId.value)
    const nodes = (graphRes.data.nodes ?? []) as AgentGraphNode[]
    const edges = (graphRes.data.edges ?? []) as AgentGraphEdge[]

    await nextTick()
    if (graph.value) {
      nodeMap.value.clear()
      graph.value.clearCells()

      nodes.forEach((node: AgentGraphNode, index: number) => {
        const nodeId = String(node.id)
        const nodeType = nodeTypes.find((nt) => nt.type === node.node_type)
        if (!nodeType) return

        const position = {
          x: 100 + (index % 4) * 200,
          y: 100 + Math.floor(index / 4) * 110,
        }

        const iconSvg = getNodeIconSvg(node.node_type)

        graph.value!.addNode({
          id: nodeId,
          shape: 'agent-graph-node',
          x: position.x,
          y: position.y,
          attrs: {
            icon: { xlinkHref: iconSvg },
            label: { text: node.name || nodeType.label },
          },
          data: { node_type: node.node_type },
        })

        nodeMap.value.set(nodeId, {
          id: node.id,
          name: node.name || nodeType.label,
          node_type: node.node_type,
          config: node.config || '',
          description: node.description || '',
        })

        applyPortsForNode(nodeId, node.node_type, node.node_type === 'condition' ? getRouteCountFromConfig(node.config) : undefined)
      })

      // from_node_slot=源节点输出 slot → output port；to_node_slot=目标节点输入 slot → input port
      edges.forEach((edge: AgentGraphEdge) => {
        const fromSlot = Number(edge.from_node_slot || 0)
        const toSlot = Number(edge.to_node_slot || 0)
        graph.value!.addEdge({
          shape: 'agent-graph-edge',
          source: { cell: String(edge.from_node_id), port: getOutputPortIdBySlot(fromSlot) },
          target: { cell: String(edge.to_node_id), port: getInputPortIdBySlot(toSlot) },
        })
      })
    }
  } catch (error: any) {
    message.error('加载数据失败')
  }
}

/** 拉取 LLM、工具、智能体列表，供右侧表单下拉使用 */
const loadOptions = async () => {
  try {
    const [llmsRes, toolsRes, agentsRes] = await Promise.all([
      getLlms({ skip: 0, limit: 1000 }),
      getTools({ skip: 0, limit: 1000 }),
      getAgents({ skip: 0, limit: 1000 }),
    ])
    llmOptions.value = (llmsRes.data ?? []).map((llm: any) => ({ label: `${llm.provider} - ${llm.model}`, value: llm.id }))
    toolOptions.value = (toolsRes.data ?? []).map((t: any) => ({ label: t.tool, value: t.id }))
    agentOptions.value = (agentsRes.data ?? [])
      .filter((a: any) => a.id !== agentId.value)
      .map((a: any) => ({ label: a.name, value: a.id }))
  } catch (error) {
    console.error('加载选项数据失败', error)
  }
}

const filterOption = (input: string, option: { label?: string }) =>
  (option.label ?? '').toLowerCase().includes(input.toLowerCase())

/** 先将当前表单 flush 到 nodeMap，再从 nodeMap 与画布边组装 nodes/edges 调 saveAgentGraph，成功后重载 */
const handleSave = async () => {
  if (!graph.value) return
  if (!agentId.value || agentId.value <= 0) {
    message.warning('请先创建并保存智能体基本信息')
    return
  }

  flushSelectedNodeConfig()

  saving.value = true
  try {
    const graphNodes = graph.value.getNodes()
    const graphEdges = graph.value.getEdges()

    const nodesData: AgentGraphNode[] = graphNodes.map((node) => {
      const nodeId = String(node.id)
      const nodeData = nodeMap.value.get(nodeId) || {
        id: Number(nodeId) || 0,
        node_type: (node.getData() as { node_type?: string })?.node_type || 'llm',
        name: '',
        description: '',
        config: '',
      }
      return {
        id: nodeData.id,
        name: nodeData.name || (node.getAttrs()?.label as any)?.text || '',
        node_type: nodeData.node_type,
        config: nodeData.config || '',
        description: nodeData.description || '',
      }
    })

    // from_node_slot=源 output port 对应 slot，to_node_slot=目标 input port 对应 slot
    const edgesData: AgentGraphEdge[] = graphEdges
      .map((edge) => {
        const source = edge.getSource() as { port?: string }
        const target = edge.getTarget() as { port?: string }
        const fromId = Number(edge.getSourceCellId())
        const toId = Number(edge.getTargetCellId())
        if (Number.isNaN(fromId) || Number.isNaN(toId)) return null
        return {
          from_node_id: fromId,
          to_node_id: toId,
          from_node_slot: getSlotByOutputPortId(source?.port),
          to_node_slot: getSlotByInputPortId(target?.port),
        }
      })
      .filter((e): e is AgentGraphEdge => e != null)

    await saveAgentGraph(agentId.value, { nodes: nodesData, edges: edgesData })

    // 重新加载数据以获取最新的ID
    await loadAgentData()

    message.success('保存成功')
  } catch (error: any) {
    message.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

// ========== 删除与导航 ==========

const handleDeleteNode = (nodeIdStr: string) => {
  if (!graph.value) return
  graph.value.removeCell(nodeIdStr)
  nodeMap.value.delete(nodeIdStr)

  if (selectedNode.value && String(selectedNode.value.id) === nodeIdStr) {
    selectedNode.value = null
  }
}

// 删除边
const handleDeleteEdge = (edgeIdStr: string) => {
  if (!graph.value) return
  graph.value.removeCell(edgeIdStr)
}

const handleBack = () => router.push('/admin/agents')

// ========== 生命周期 ==========

onMounted(async () => {
  await loadOptions()
  await nextTick()
  initGraph()
})

onBeforeUnmount(() => {
  if (graph.value) {
    graph.value.dispose()
  }
})
</script>

<style scoped>
.agent-editor {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.editor-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #e8e8e8;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-left {
  width: 160px;
  border-right: 1px solid #e8e8e8;
  overflow-y: auto;
}

.node-palette {
  padding: 16px;
}

.node-item {
  display: flex;
  align-items: center;
  padding: 6px;
  margin-bottom: 8px;
  border: 1px solid #5F95FF;
  border-radius: 4px;
  cursor: move;
}

.node-item:hover {
  border-color: #1890ff;
}

.node-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  margin-right: 4px;
}

.node-icon img {
  width: 18px;
  height: 18px;
  object-fit: contain;
}

.node-label {
  font-size: 12px;
}

.editor-center {
  flex: 1;
  position: relative;
}

.graph-container {
  width: 100%;
  height: 100%;
}

.editor-right {
  width: 320px;
  border-left: 1px solid #e8e8e8;
  overflow-y: auto;
}

.config-empty {
  padding-top: 64px;
}

.config-panel {
  padding: 16px;
}

.config-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

.card-title-icon {
  width: 18px;
  height: 18px;
}

.route-mapping-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
