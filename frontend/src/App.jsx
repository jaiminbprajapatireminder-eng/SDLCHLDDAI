import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { downloadPdf, downloadExcel, downloadTxt } from './download'
import mermaid from 'mermaid'

const tabs = [
  'dashboard',
  'features',
  'stories',
  'testing',
  'architecture',
  'structure',
  'chatbot',
  'agent',
]

const EMPTY_PAYLOAD = {
  title: '',
  summary: '',
  functional_requirements: [],
  project_management_tool: 'Not specified',
  repository: 'Not specified',
  ci_cd_pipeline: 'Not specified',
  technology_stack: [],
  acceptance_criteria: [],
  architecture_notes: [],
  architecture_diagram: { nodes: [], edges: [], cloud_services: [] },
  project_structure: [],
  features: [],
  stories: [],
  testing_stories: [],
}

function formatList(items) {
  if (!items?.length) return ['No data yet. Upload an HLDD document to get started.']
  return items
}

function getTechnologyBadgeClass(item) {
  const normalized = String(item || '').toLowerCase()

  if (normalized.includes('aws') || normalized.includes('azure') || normalized.includes('gcp') || normalized.includes('google cloud')) {
    return 'tech-pill-cloud'
  }

  if (normalized.includes('react') || normalized.includes('angular') || normalized.includes('vue') || normalized.includes('next')) {
    return 'tech-pill-frontend'
  }

  if (normalized.includes('fastapi') || normalized.includes('spring boot') || normalized.includes('node') || normalized.includes('java') || normalized.includes('.net')) {
    return 'tech-pill-backend'
  }

  if (normalized.includes('postgres') || normalized.includes('mysql') || normalized.includes('mongo') || normalized.includes('oracle') || normalized.includes('sql')) {
    return 'tech-pill-data'
  }

  if (normalized.includes('docker') || normalized.includes('kubernetes')) {
    return 'tech-pill-runtime'
  }

  return 'tech-pill-default'
}

function buildProjectTree(projectStructure = []) {
  const root = { name: 'Project Root', isDirectory: true, children: [] }

  projectStructure.forEach((item) => {
    const normalized = String(item || '').trim()
    if (!normalized) {
      return
    }

    const cleaned = normalized.replace(/\/+$|\\+$/g, '')
    const parts = cleaned.split(/[\\/]+/).filter(Boolean)
    if (!parts.length) {
      return
    }

    let current = root

    parts.forEach((part, index) => {
      const isDirectory = index < parts.length - 1 || normalized.endsWith('/')
      const existing = current.children.find((child) => child.name === part)

      if (existing) {
        existing.isDirectory = existing.isDirectory || isDirectory
        current = existing
        return
      }

      const nextNode = {
        name: part,
        isDirectory,
        children: [],
      }

      current.children.push(nextNode)
      current = nextNode
    })
  })

  return root
}

function serializeTreeToText(node, prefix = '', isLast = true, isRoot = true) {
  if (isRoot) {
    let result = node.name + (node.isDirectory ? '/' : '') + '\n'
    const children = node.children || []
    for (let i = 0; i < children.length; i++) {
      result += serializeTreeToText(children[i], '', i === children.length - 1, false)
    }
    return result
  }

  const connector = isLast ? '└── ' : '├── '
  let result = prefix + connector + node.name + (node.isDirectory ? '/' : '') + '\n'
  const children = node.children || []
  const childPrefix = prefix + (isLast ? '    ' : '│   ')
  for (let i = 0; i < children.length; i++) {
    result += serializeTreeToText(children[i], childPrefix, i === children.length - 1, false)
  }
  return result
}

function ProjectTreeNode({ node }) {
  return (
    <li className="structure-tree-item">
      <span className={node.isDirectory ? 'structure-node structure-dir' : 'structure-node structure-file'}>
        {node.isDirectory ? '📁' : '📄'} {node.name}
      </span>
      {node.children?.length > 0 && (
        <ul className="structure-tree">
          {node.children.map((child, index) => (
            <ProjectTreeNode key={`${child.name}-${index}`} node={child} />
          ))}
        </ul>
      )}
    </li>
  )
}

function flattenStructureToRows(node, depth = 0, rows = []) {
  rows.push({ name: node.name, type: node.isDirectory ? 'folder' : 'file', depth })
  for (const child of (node.children || [])) {
    flattenStructureToRows(child, depth + 1, rows)
  }
  return rows
}

function getProjectStructureSummary(root) {
  const stats = {
    topLevel: root.children?.length || 0,
    directories: 0,
    files: 0,
  }

  const walk = (node) => {
    if (!node) {
      return
    }

    if (node.isDirectory) {
      stats.directories += 1
      node.children?.forEach(walk)
      return
    }

    stats.files += 1
  }

  root.children?.forEach(walk)

  return stats
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [data, setData] = useState(null)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('Upload a High Level Design Document to generate insights.')
  const [showCloudExpanded, setShowCloudExpanded] = useState(false)
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null)
  const [hasUploadedDocument, setHasUploadedDocument] = useState(false)
  const [chatbotPrompt, setChatbotPrompt] = useState('')
  const [chatbotPriority, setChatbotPriority] = useState('balanced')
  const [chatbotResponse, setChatbotResponse] = useState('')
  const [chatbotError, setChatbotError] = useState('')
  const [chatbotLoading, setChatbotLoading] = useState(false)
  const [agentMessages, setAgentMessages] = useState([])
  const [agentInput, setAgentInput] = useState('')
  const [agentLoading, setAgentLoading] = useState(false)
  const [agentError, setAgentError] = useState('')
  const [agentFile, setAgentFile] = useState(null)
  const [agentFileText, setAgentFileText] = useState('')
  const [agentContext, setAgentContext] = useState(null)
  const [agentJiraPending, setAgentJiraPending] = useState(null)
  const [agentJiraConfirming, setAgentJiraConfirming] = useState(false)
  const [localFeatures, setLocalFeatures] = useState([])
  const [localStories, setLocalStories] = useState([])
  const [localTestingStories, setLocalTestingStories] = useState([])
  const [editingFeatureId, setEditingFeatureId] = useState(null)
  const [editingStoryId, setEditingStoryId] = useState(null)
  const [editingTestingId, setEditingTestingId] = useState(null)
  const [addingNew, setAddingNew] = useState(null) // 'feature' | 'story' | 'testing' | null
  const [jiraSyncing, setJiraSyncing] = useState(false)
  const [jiraMessage, setJiraMessage] = useState('')
  const [jiraStorySyncing, setJiraStorySyncing] = useState(false)
  const [jiraStoryMessage, setJiraStoryMessage] = useState('')
  const [jiraEpicMapping, setJiraEpicMapping] = useState({})
  const [jiraStoryMapping, setJiraStoryMapping] = useState({})
  const [jiraTestingSyncing, setJiraTestingSyncing] = useState(false)
  const [jiraTestingMessage, setJiraTestingMessage] = useState('')

  useEffect(() => {
    setLocalFeatures(data?.features || [])
    setLocalStories(data?.stories || [])
    setLocalTestingStories(data?.testing_stories || [])
    setEditingFeatureId(null)
    setEditingStoryId(null)
    setEditingTestingId(null)
    setAddingNew(null)
  }, [data])

  const nextId = (prefix, items) => {
    const nums = items.map((f) => {
      const m = f.id.match(/(\d+)$/)
      return m ? parseInt(m[1], 10) : 0
    })
    const max = nums.length ? Math.max(...nums) : 0
    return `${prefix}${String(max + 1).padStart(3, '0')}`
  }

  const addFeature = (feature) => setLocalFeatures((prev) => [...prev, { ...feature, id: nextId('IPMA#', prev) }])
  const updateFeature = (id, updates) => setLocalFeatures((prev) => prev.map((f) => (f.id === id ? { ...f, ...updates } : f)))
  const deleteFeature = (id) => setLocalFeatures((prev) => prev.filter((f) => f.id !== id))

  const addStory = (story) => setLocalStories((prev) => [...prev, { ...story, id: nextId('E-CRM#', prev) }])
  const updateStory = (id, updates) => setLocalStories((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)))
  const deleteStory = (id) => setLocalStories((prev) => prev.filter((s) => s.id !== id))

  const addTestingStory = (story) => setLocalTestingStories((prev) => [...prev, { ...story, id: nextId('TEST-E-CRM#', prev) }])
  const updateTestingStory = (id, updates) => setLocalTestingStories((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)))
  const deleteTestingStory = (id) => setLocalTestingStories((prev) => prev.filter((s) => s.id !== id))
  const mermaidRef = useRef(null)
  const modalMermaidRef = useRef(null)
  const dashboardRef = useRef(null)
  const featuresRef = useRef(null)
  const storiesRef = useRef(null)
  const testingRef = useRef(null)
  const architectureRef = useRef(null)
  const structureRef = useRef(null)

  const updateLastRefreshedAt = () => {
    setLastRefreshedAt(new Date())
  }

  const clearPayloadState = (nextMessage = 'Upload a High Level Design Document to generate insights.') => {
    setData(null)
    setHasUploadedDocument(false)
    setLastRefreshedAt(null)
    setShowCloudExpanded(false)
    setFile(null)
    setChatbotPrompt('')
    setChatbotPriority('balanced')
    setChatbotResponse('')
    setChatbotError('')
    setMessage(nextMessage)
  }

  const refreshData = async ({ notify = false, forceClear = false } = {}) => {
    if (forceClear) {
      clearPayloadState('Payload cleared. Upload an HLDD document to generate the dashboard again.')
      if (notify) {
        setMessage('Payload cleared. Upload an HLDD document to generate the dashboard again.')
      }
      return null
    }

    try {
      const response = await fetch('http://localhost:8000/api/hldd')

      if (!response.ok) {
        throw new Error('Unable to load the latest payload.')
      }

      const payload = await response.json()
      const hasPayload = Boolean(payload && payload.title && payload.title !== 'No HLDD uploaded yet')

      if (!hasPayload) {
        clearPayloadState('No HLDD uploaded. Upload a document to generate the dashboard.')
        if (notify) {
          setMessage('No HLDD uploaded. Upload a document to generate the dashboard.')
        }
        return null
      }

      setData(payload)
      setHasUploadedDocument(true)
      setChatbotPrompt('')
      setChatbotResponse('')
      setChatbotError('')
      updateLastRefreshedAt()
      setMessage(`Live payload loaded: ${payload.title}`)
      return payload
    } catch (error) {
      clearPayloadState(error.message || 'Unable to refresh the payload.')
      if (notify) {
        setMessage(error.message || 'Unable to refresh the payload.')
      }
      return null
    }
  }

  useEffect(() => {
    refreshData()
  }, [])

  useEffect(() => {
    setShowCloudExpanded(false)
  }, [data])

  const defaultMermaidChart = useMemo(() => `
%%{init: {'theme': 'base', 'flowchart': {'curve': 'basis', 'nodeSpacing': 150, 'rankSpacing': 200}, 'themeVariables': {'primaryColor': '#0f172a', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#334155', 'lineColor': '#93c5fd', 'secondaryColor': '#111827', 'tertiaryColor': '#0b1120', 'fontSize': '15px'}}}%%
flowchart LR
    classDef frontend fill:#0f172a,stroke:#38bdf8,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18
    classDef backend fill:#111827,stroke:#818cf8,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18
    classDef data fill:#0b1120,stroke:#4ade80,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18
    classDef container fill:#111827,stroke:#f59e0b,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18
    classDef delivery fill:#111827,stroke:#f472b6,color:#f8fafc,stroke-width:1.8px,rx:18,ry:18
    linkStyle default stroke:#93c5fd,stroke-width:2.2px

    subgraph UI[Presentation]
        F["🖥️ React UI"]
    end

    subgraph API[Application]
        B["🔧 FastAPI Services"]
    end

    subgraph DATA_LAYER[Persistence]
        D["🗄️ PostgreSQL"]
    end

    subgraph OPS[Runtime & Containers]
        C["🐳 Docker"]
    end

    subgraph DELIVERY_LAYER[Delivery Governance]
        M["📋 Jira Delivery"]
    end

    F -->|Calls| B
    B -->|Stores| D
    C -->|Runs UI| F
    C -->|Runs APIs| B
    M -->|Tracks UI work| F
    M -->|Tracks API work| B
    M -->|Tracks data work| D

    class F frontend
    class B backend
    class D data
    class C container
    class M delivery
`, [])

  const architectureDiagram = data?.architecture_diagram || null
  const cloudServices = architectureDiagram?.cloud_services || []
  const hasCloudExpansion = Boolean(architectureDiagram?.expanded_diagram && cloudServices.length > 0)

  const mermaidChart = useMemo(() => {
    if (!data) {
      return ''
    }

    if (showCloudExpanded && hasCloudExpansion) {
      return architectureDiagram.expanded_diagram
    }

    return architectureDiagram?.diagram || defaultMermaidChart
  }, [architectureDiagram, data, defaultMermaidChart, hasCloudExpansion, showCloudExpanded])

  const featureStoryTotals = useMemo(() => {
    const totals = {}

    ;(localStories || []).forEach((story) => {
      totals[story.feature_id] = (totals[story.feature_id] || 0) + (Number(story.story_points) || 0)
    })

    ;(localTestingStories || []).forEach((story) => {
      const featureId = localStories?.find((item) => item.id === story.related_story_id)?.feature_id
      if (!featureId) {
        return
      }

      totals[featureId] = (totals[featureId] || 0) + (Number(story.story_points) || 0)
    })

    return totals
  }, [localStories, localTestingStories])

  const featureTestingStoryTotals = useMemo(() => {
    const totals = {}

    ;(localTestingStories || []).forEach((story) => {
      const featureId = localStories?.find((item) => item.id === story.related_story_id)?.feature_id
      if (!featureId) {
        return
      }

      totals[featureId] = (totals[featureId] || 0) + (Number(story.story_points) || 0)
    })

    return totals
  }, [localStories, localTestingStories])

  const technologyStack = data?.technology_stack || []
  const cloudProvider = useMemo(() => {
    const provider = technologyStack.find((item) => ['AWS', 'Azure', 'Google Cloud', 'GCP'].includes(String(item)))
    return provider || 'Not specified'
  }, [technologyStack])

  const totalStoryPoints = useMemo(() => {
    const developmentPoints = (localStories || []).reduce((sum, story) => sum + (Number(story.story_points) || 0), 0)
    const testingPoints = (localTestingStories || []).reduce((sum, story) => sum + (Number(story.story_points) || 0), 0)

    return developmentPoints + testingPoints
  }, [localStories, localTestingStories])

  const recommendedLLM = useMemo(() => {
    const stack = new Set(data?.technology_stack || [])

    if (stack.has('Google Cloud') || stack.has('GCP')) {
      return {
        provider: 'Google Gemini',
        model: 'gemini-2.0-flash → gemini-2.5-flash',
        reason: 'Gemini Dataflow pipeline — best fit for GCP and cloud-specific delivery guidance.',
      }
    }

    if (stack.has('React') && stack.has('FastAPI') && stack.has('PostgreSQL') && stack.has('Docker')) {
      return {
        provider: 'OpenAI',
        model: 'gpt-4.1-mini',
        reason: 'Best fit for a React + FastAPI + PostgreSQL + Docker delivery workflow.',
      }
    }

    return {
      provider: 'OpenAI',
      model: 'gpt-4o-mini',
      reason: 'General-purpose delivery support for HLDD analysis and planning.',
    }
  }, [data?.technology_stack])

  const summaryStats = useMemo(() => [
    {
      label: 'Features',
      value: localFeatures.length,
      subtitle: localFeatures.length === 1 ? 'feature to deliver' : 'features to deliver',
    },
    {
      label: 'Development Stories',
      value: localStories.length,
      subtitle: localStories.length === 1 ? 'development story to implement' : 'development stories to implement',
    },
    {
      label: 'Testing Stories',
      value: localTestingStories.length,
      subtitle: localTestingStories.length === 1 ? 'testing story to execute' : 'testing stories to execute',
    },
    {
      label: 'Total Story Points',
      value: totalStoryPoints,
      subtitle: `${recommendedLLM.provider} suggested for the current stack`,
    },
  ], [cloudProvider, localFeatures.length, localStories.length, localTestingStories.length, recommendedLLM.model, recommendedLLM.provider, totalStoryPoints])

  const chatbotPrompts = useMemo(() => {
    if (!data) {
      return [
        'Summarize the current HLDD context and next delivery steps.',
        'What frontend, backend, and cloud options fit this project?',
        'Show me a cost breakdown and alternatives for a mid-size budget.',
      ]
    }

    return [
      `Summarize the ${data.title || 'uploaded HLDD'} delivery plan and next milestones.`,
      `What frontend, backend, and cloud options fit ${data.title || 'this project'}?`,
      `Show me a cost breakdown, efficiency, security, and turnaround tradeoff for ${data.title || 'this project'}.`,
      `Compare AWS, Azure, and GCP service offerings and pricing for ${data.title || 'the project'}.`,
      `Identify the top three risks and mitigation actions for ${data.project_management_tool || 'the project'}.`,
      `Draft a concise kickoff briefing for the ${data.technology_stack?.join(', ') || 'selected stack'} implementation team.`,
    ]
  }, [data])

  const agentPrompts = useMemo(() => [
    'Parse this HLDD and summarize the delivery plan',
    'Create Epics, Stories, and Subtasks in JIRA for all features',
    'Compare AWS vs GCP for this project',
    'What are the top risks and mitigations?',
    'Generate a project plan with stories and test cases',
  ], [])

  const handleChatbotGenerate = async () => {
    if (!data) {
      setChatbotError('Upload an HLDD document first so the chatbot can use the extracted context.')
      return
    }

    const prompt = chatbotPrompt.trim() || chatbotPrompts[0]
    setChatbotLoading(true)
    setChatbotError('')
    setChatbotResponse('')

    try {
      const response = await fetch('http://localhost:8000/api/chatbot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt, priority: chatbotPriority }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Unable to generate a chatbot response.')
      }

      const payload = await response.json()
      setChatbotPrompt(prompt)
      setChatbotResponse(payload.response || 'No response was returned.')
    } catch (error) {
      setChatbotError(error.message || 'Unable to generate a chatbot response.')
    } finally {
      setChatbotLoading(false)
    }
  }

  const handleAgentFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setAgentFile(file)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('http://localhost:8000/api/agent/parse-document', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Parsing failed')
      }
      const data = await res.json()
      setAgentFileText(data.text)
      const shortName = data.filename.replace(/\.(pdf|docx|txt|md)$/i, '')
      setAgentMessages(prev => [...prev, { role: 'user', content: `Uploaded document (${data.length} chars): ${shortName}` }])
    } catch (err) {
      setAgentError(err.message || 'Could not read file.')
    }
  }

  const handleAgentSend = async () => {
    const prompt = agentInput.trim()
    if (!prompt && !agentFileText) return

    const hlddText = agentFileText || ''

    if (prompt) {
      setAgentMessages(prev => [...prev, { role: 'user', content: prompt }])
    }

    setAgentLoading(true)
    setAgentError('')
    setAgentJiraPending(null)

    const history = agentMessages.map(m => ({ role: m.role, content: m.content }))

    try {
      const response = await fetch('http://localhost:8000/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt || 'Parse this HLDD document', hldd_text: hlddText, history }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Agent request failed.')
      }

      const payload = await response.json()
      setAgentMessages(prev => [...prev, { role: 'assistant', content: payload.response }])
      if (payload.state?.parsed || payload.state?.plan) {
        setAgentContext(payload.state)
      }
      if (payload.jira_pending) {
        setAgentJiraPending(payload.jira_pending)
      }
      setAgentInput('')
      setAgentFile(null)
      setAgentFileText('')
    } catch (error) {
      setAgentError(error.message || 'Agent request failed.')
    } finally {
      setAgentLoading(false)
    }
  }

  const handleJiraApprove = async () => {
    const plan = agentContext?.plan
    if (!plan) return

    setAgentJiraConfirming(true)
    setAgentError('')
    try {
      const response = await fetch('http://localhost:8000/api/agent/confirm-jira', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan }),
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'JIRA creation failed.')
      }
      const result = await response.json()
      const epicCount = result.results?.epics?.length || 0
      const storyCount = result.results?.stories?.length || 0
      const testCount = result.results?.testing?.length || 0
      const keys = [
        ...(result.results?.epics || []).map(e => e.jira_key),
        ...(result.results?.stories || []).map(s => s.jira_key),
        ...(result.results?.testing || []).map(t => t.jira_key),
      ]
      setAgentMessages(prev => [...prev, {
        role: 'assistant',
        content: `✅ **JIRA items created successfully!**\n\n• ${epicCount} Epic(s)\n• ${storyCount} Story(ies)\n• ${testCount} Subtask(s)\n\nKeys: ${keys.join(', ')}`
      }])
      setAgentJiraPending(null)
      setAgentContext(prev => prev ? {
        ...prev,
        epics: { ...(prev.epics || {}), ...result.epic_mapping },
        stories: { ...(prev.stories || {}), ...result.story_mapping },
      } : prev)
    } catch (error) {
      setAgentError(error.message || 'JIRA confirmation failed.')
    } finally {
      setAgentJiraConfirming(false)
    }
  }

  const handleJiraDeny = async () => {
    setAgentMessages(prev => [...prev, {
      role: 'assistant',
      content: '❌ JIRA creation was cancelled.'
    }])
    setAgentJiraPending(null)
  }

  useEffect(() => {
    if (activeTab !== 'architecture' || !mermaidRef.current) {
      return
    }

    let cancelled = false

    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      securityLevel: 'loose',
      flowchart: {
        curve: 'basis',
        nodeSpacing: 150,
        rankSpacing: 200,
      },
    })

    const attachCloudNodeInteractivity = () => {
      if (!mermaidRef.current || !hasCloudExpansion) {
        return
      }

      const cloudNodes = Array.from(mermaidRef.current.querySelectorAll('g.node')).filter((node) => {
        const text = node.textContent || ''
        return text.includes('AWS Cloud') || text.includes('Azure Cloud') || text.includes('GCP Cloud')
      })

      cloudNodes.forEach((node) => {
        node.style.cursor = 'pointer'
        node.setAttribute('role', 'button')
        node.setAttribute('tabindex', '0')
        node.setAttribute('title', 'Click to toggle expanded cloud recommendations')
        node.setAttribute('aria-label', 'Toggle expanded cloud recommendations')

        const toggleCloudRecommendations = () => {
          setShowCloudExpanded((current) => !current)
        }

        node.onclick = toggleCloudRecommendations
        node.onkeydown = (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            toggleCloudRecommendations()
          }
        }
      })
    }

    const renderDiagram = async () => {
      try {
        const { svg } = await mermaid.render('architecture-diagram', mermaidChart)
        if (!cancelled && mermaidRef.current) {
          mermaidRef.current.innerHTML = svg
          attachCloudNodeInteractivity()
        }
      } catch (error) {
        if (!cancelled && mermaidRef.current) {
          mermaidRef.current.innerHTML = '<p class="note">Unable to render the architecture diagram.</p>'
        }
      }
    }

    renderDiagram()

    return () => {
      cancelled = true
    }
  }, [activeTab, mermaidChart, hasCloudExpansion])

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!file) {
      setMessage('Please choose an HLDD file first.')
      return
    }

    setLoading(true)
    setMessage('Parsing and generating the delivery plan...')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const payload = await response.json()
      setData(payload)
      setHasUploadedDocument(true)
      setChatbotPrompt('')
      setChatbotResponse('')
      setChatbotError('')
      updateLastRefreshedAt()
      setMessage(`HLDD processed successfully: ${payload.title}`)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  const JIRA_BASE_URL = 'https://mylearningdata.atlassian.net'

  const syncFeaturesToJira = async () => {
    setJiraSyncing(true)
    setJiraMessage('')
    try {
      const response = await fetch('http://localhost:8000/api/jira/create-features', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: localFeatures }),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'JIRA sync failed')
      }
      const mapping = {}
      const msgs = result.results.map((r) => {
        if (r.success) {
          mapping[r.feature_id] = r.jira_key
          return `✓ ${r.feature_id} — ${r.jira_key}`
        }
        return `✗ ${r.feature_id} — ${r.error}`
      })
      setJiraEpicMapping(mapping)
      setJiraMessage(msgs.join('\n'))
    } catch (error) {
      setJiraMessage(`Error: ${error.message}`)
    } finally {
      setJiraSyncing(false)
    }
  }

  const syncStoriesToJira = async () => {
    setJiraStorySyncing(true)
    setJiraStoryMessage('')
    try {
      const response = await fetch('http://localhost:8000/api/jira/create-stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stories: localStories, epic_mapping: jiraEpicMapping }),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'JIRA story sync failed')
      }
      const mapping = {}
      const msgs = result.results.map((r) => {
        if (r.success) {
          mapping[r.story_id] = r.jira_key
          return `✓ ${r.story_id} → ${r.jira_key} (Epic: ${r.parent_epic || 'none'})`
        }
        return `✗ ${r.story_id} — ${r.error}`
      })
      setJiraStoryMapping(mapping)
      setJiraStoryMessage(msgs.join('\n'))
    } catch (error) {
      setJiraStoryMessage(`Error: ${error.message}`)
    } finally {
      setJiraStorySyncing(false)
    }
  }

  const syncTestingStoriesToJira = async () => {
    setJiraTestingSyncing(true)
    setJiraTestingMessage('')
    try {
      const response = await fetch('http://localhost:8000/api/jira/create-testing-stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ testing_stories: localTestingStories, story_mapping: jiraStoryMapping }),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || 'JIRA testing sync failed')
      }
      const msgs = result.results.map((r) =>
        r.success
          ? `✓ ${r.test_id} → ${r.jira_key} (Story: ${r.parent_story || 'none'})`
          : `✗ ${r.test_id} — ${r.error}`
      )
      setJiraTestingMessage(msgs.join('\n'))
    } catch (error) {
      setJiraTestingMessage(`Error: ${error.message}`)
    } finally {
      setJiraTestingSyncing(false)
    }
  }

  const architectureNodes = useMemo(() => data?.architecture_diagram?.nodes || [], [data])
  const architectureEdges = useMemo(() => data?.architecture_diagram?.edges || [], [data])
  const projectStructureTree = useMemo(() => buildProjectTree(data?.project_structure || []), [data?.project_structure])
  const structureSummary = useMemo(() => getProjectStructureSummary(projectStructureTree), [projectStructureTree])
  const cloudNode = useMemo(() => architectureNodes.find((node) => node.id === 'cloud'), [architectureNodes])
  const cloudServiceMeta = {
    ECS: {
      icon: '🧩',
      description: 'Container orchestration for API and worker workloads.',
      tier: 'Primary',
      summary: 'Use for containerized services that need predictable scaling and clear deployment boundaries.',
    },
    EC2: {
      icon: '🖥️',
      description: 'Virtual compute for controlled runtime placement.',
      tier: 'Secondary',
      summary: 'Use for workloads that need explicit instance sizing or long-running operational control.',
    },
    Lambda: {
      icon: '⚡',
      description: 'Event-driven execution for bursty or serverless workloads.',
      tier: 'Optional',
      summary: 'Use for event-triggered processing, background jobs, and bursty automation.',
    },
    AKS: {
      icon: '🚀',
      description: 'Managed Kubernetes for containerized services.',
      tier: 'Primary',
      summary: 'Use when the platform needs a managed Kubernetes control plane and container portability.',
    },
    'App Service': {
      icon: '🌐',
      description: 'Managed web hosting for app frontends and APIs.',
      tier: 'Secondary',
      summary: 'Use for managed hosting where app deployment and routing should remain simple and predictable.',
    },
    'Azure Functions': {
      icon: '⚡',
      description: 'Serverless execution for event-based workflows.',
      tier: 'Optional',
      summary: 'Use for event-driven workflows and lightweight background processing.',
    },
    GKE: {
      icon: '🚀',
      description: 'Managed Kubernetes for containerized deployments.',
      tier: 'Primary',
      summary: 'Use for containerized workloads that need managed Kubernetes orchestration and scale.',
    },
    'Cloud Run': {
      icon: '☁️',
      description: 'Managed containers for lightweight runtime services.',
      tier: 'Primary',
      summary: 'Use for stateless services that benefit from automatic scaling and minimal operational overhead.',
    },
    'Cloud Functions': {
      icon: '⚡',
      description: 'Serverless compute for lightweight automation.',
      tier: 'Optional',
      summary: 'Use for lightweight event handlers and automation jobs that do not require a long-running process.',
    },
    'Amazon RDS for PostgreSQL': {
      icon: '🗄️',
      description: 'Managed relational database for transactional and reporting workloads.',
      tier: 'Primary',
      summary: 'Use for durable PostgreSQL storage with managed backups, patching, and operational controls.',
    },
    'Aurora DB': {
      icon: '🛢️',
      description: 'High-performance relational database service for scalable transactional workloads.',
      tier: 'Primary',
      summary: 'Use when the platform needs a scalable relational database with high availability and fast performance.',
    },
    'Azure Database for PostgreSQL': {
      icon: '🗄️',
      description: 'Azure-managed PostgreSQL for application and reporting workloads.',
      tier: 'Primary',
      summary: 'Use for managed PostgreSQL storage with Azure-native monitoring and governance.',
    },
    'Cloud SQL for PostgreSQL': {
      icon: '🗄️',
      description: 'Managed PostgreSQL service for Google Cloud workloads.',
      tier: 'Primary',
      summary: 'Use for managed PostgreSQL with native GCP integration and minimal platform operations.',
    },
  }
  const cloudServicesByTier = useMemo(() => {
    const primary = []
    const secondary = []
    const optional = []

    cloudServices.forEach((service) => {
      const tier = cloudServiceMeta[service]?.tier || 'Optional'

      if (tier === 'Primary') {
        primary.push(service)
      } else if (tier === 'Secondary') {
        secondary.push(service)
      } else {
        optional.push(service)
      }
    })

    return { Primary: primary, Secondary: secondary, Optional: optional }
  }, [cloudServices])
  const cloudRecommendationSummary = useMemo(() => {
    const providerLabel = cloudNode?.label || 'Cloud'

    if (providerLabel.includes('AWS')) {
      return 'AWS recommendation: combine ECS for container orchestration, EC2 for baseline compute, Lambda for bursty workflows, and a managed PostgreSQL option such as Amazon RDS for PostgreSQL or Aurora DB.'
    }

    if (providerLabel.includes('Azure')) {
      return 'Azure recommendation: combine AKS for managed containers, App Service for hosted application tiers, Azure Functions for serverless execution, and Azure Database for PostgreSQL for relational persistence.'
    }

    if (providerLabel.includes('GCP')) {
      return 'GCP recommendation: balance GKE or Cloud Run for containers, Cloud Functions for serverless automation, and Cloud SQL for PostgreSQL for managed relational storage.'
    }

    return 'Cloud recommendation: use the expanded service list to align the platform choice with runtime, scale, and operational needs.'
  }, [cloudNode])
  const legendLabels = useMemo(() => {
    const labels = []

    const frontendNodes = architectureNodes.filter((n) => n.type === 'frontend')
    if (frontendNodes.length) {
      labels.push({ key: 'frontend', label: 'Frontend', nodes: frontendNodes })
    }

    const backendNodes = architectureNodes.filter((n) => n.type === 'backend')
    if (backendNodes.length) {
      labels.push({ key: 'backend', label: 'Backend', nodes: backendNodes })
    }

    const dataNodes = architectureNodes.filter((n) => n.type === 'data')
    if (dataNodes.length) {
      labels.push({ key: 'data', label: 'Data Store', nodes: dataNodes })
    }

    if (architectureNodes.some((n) => n.id === 'cloud')) {
      labels.push({ key: 'cloud', label: cloudNode?.label || 'Cloud', nodes: [cloudNode] })
    }

    const repoNode = architectureNodes.find((n) => n.id === 'repository')
    if (repoNode) {
      labels.push({ key: 'repository', label: 'Repository', nodes: [repoNode] })
    }

    const runtimeNode = architectureNodes.find((n) => n.id === 'runtime')
    if (runtimeNode) {
      labels.push({ key: 'runtime', label: 'Runtime', nodes: [runtimeNode] })
    }

    const containerNode = architectureNodes.find((n) => n.id === 'container')
    if (containerNode) {
      labels.push({ key: 'container', label: 'Container', nodes: [containerNode] })
    }

    const deliveryNode = architectureNodes.find((n) => n.id === 'delivery')
    if (deliveryNode) {
      labels.push({ key: 'delivery', label: 'Delivery', nodes: [deliveryNode] })
    }

    return labels
  }, [architectureNodes, cloudNode])

  const [expandedLegends, setExpandedLegends] = useState({})
  const [diagramModalOpen, setDiagramModalOpen] = useState(false)

  useEffect(() => {
    if (diagramModalOpen && modalMermaidRef.current && mermaidRef.current) {
      const svg = mermaidRef.current.querySelector('svg')
      if (svg) {
        modalMermaidRef.current.innerHTML = ''
        modalMermaidRef.current.appendChild(svg.cloneNode(true))
      }
    }
  }, [diagramModalOpen])

  const handleLegendToggle = useCallback((key) => {
    setExpandedLegends((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const handleCloudToggle = () => {
    if (!hasCloudExpansion) {
      return
    }

    setShowCloudExpanded((current) => !current)
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">
            <svg className="hero-ai-icon" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <defs>
                <linearGradient id="hero-robot-grad" x1="2" y1="2" x2="34" y2="34">
                  <stop offset="0%" stopColor="#38bdf8"/>
                  <stop offset="50%" stopColor="#818cf8"/>
                  <stop offset="100%" stopColor="#c084fc"/>
                </linearGradient>
              </defs>
              <rect x="4" y="7" width="28" height="22" rx="7" stroke="url(#hero-robot-grad)" strokeWidth="1.8" fill="rgba(56,189,248,0.05)"/>
              <circle cx="12" cy="18" r="3" fill="#94a3b8"/>
              <circle cx="24" cy="18" r="3" fill="#94a3b8"/>
              <path d="M14 25c2 1.8 6 1.8 8 0" stroke="url(#hero-robot-grad)" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M18 2v4M9 4l2 3M27 4l-2 3M11 31v2M18 29v4M25 31v2" stroke="url(#hero-robot-grad)" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            HLDD AI Agent
          </p>
          <h1>Upload your High Level Design Document and generate project delivery artifacts instantly.</h1>
          <p className="hero-copy">
            The application reads the document, extracts the technical and delivery data, and creates a live dashboard with features, stories, testing stories, architecture views, and a recommended project structure.
          </p>
        </div>
        <div className="upload-card">
          <form onSubmit={handleUpload}>
            <label htmlFor="hldd-file" className="field-label">Upload HLDD</label>
            <input id="hldd-file" type="file" accept=".txt,.md,.docx,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <div className="upload-actions">
              <button type="submit" disabled={loading}>{loading ? 'Processing...' : 'Generate Dashboard'}</button>
              <button type="button" onClick={() => refreshData({ notify: true, forceClear: true })}>Refresh payload</button>
            </div>
          </form>
          <p className="upload-file-meta">{file ? `Selected file: ${file.name}` : 'No file selected yet.'}</p>
          <p className="upload-hint">Accepted formats: .txt, .md, .docx, and .pdf. Use the sample HLDD template to explore the dashboard quickly.</p>
          <p className="status-message">{message}</p>
          <p className="refresh-meta">
            {lastRefreshedAt ? `Last refreshed at ${lastRefreshedAt.toLocaleString()}` : 'Last refreshed at —'}
          </p>
          <p className="note">The manual Refresh payload action reloads the latest cached payload from the backend and keeps the current view in sync with the last upload.</p>
          <a className="download-link" href="/sample-hldd-template.txt" download>
            Download sample HLDD template
          </a>
        </div>
      </header>

      <nav className="tab-bar">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={tab === activeTab ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(tab)}
          >
            <span className="tab-icon">
              {tab === 'dashboard' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              )}
              {tab === 'features' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              )}
              {tab === 'stories' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              )}
              {tab === 'testing' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              )}
              {tab === 'architecture' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              )}
              {tab === 'structure' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
              )}
              {tab === 'chatbot' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              )}
              {tab === 'agent' && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16.01"/><line x1="16" y1="16" x2="16" y2="16.01"/></svg>
              )}
            </span>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </nav>

      <main className="content-grid">
        {activeTab === 'dashboard' && (
          <section className="dashboard-layout" ref={dashboardRef}>
            <div className="download-bar">
              <button type="button" className="download-btn" onClick={() => downloadPdf(dashboardRef.current, 'dashboard')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
            </div>
            <div className="summary-stats">
              {summaryStats.map((stat) => (
                <div key={stat.label} className="metric-card">
                  <span className="metric-label">{stat.label}</span>
                  <strong className="metric-value">{stat.value}</strong>
                  <p className="metric-copy">{stat.subtitle}</p>
                </div>
              ))}
            </div>
            <div className="panel-grid">
              <div className="summary-card highlight">
                <h2>Title</h2>
                <p>{data?.title || 'No HLDD uploaded yet.'}</p>
              </div>
              <div className="summary-card">
                <h2>Functional Requirements</h2>
                <ul>
                  {formatList(data?.functional_requirements).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                </ul>
              </div>
              <div className="summary-card">
                <h2>Project Management Tool</h2>
                <p>{data?.project_management_tool || 'Not specified'}</p>
              </div>
              <div className="summary-card">
                <h2>Repository</h2>
                <p>{data?.repository || 'Not specified'}</p>
              </div>
              <div className="summary-card">
                <h2>Technology Stack</h2>
                <div className="stack-pills">
                  {(technologyStack.length ? technologyStack : ['No technology stack extracted yet.']).map((item) => (
                    <span key={item} className={`tech-pill ${getTechnologyBadgeClass(item)}`}>{item}</span>
                  ))}
                </div>
              </div>
              <div className="summary-card">
                <h2>Acceptance Criteria</h2>
                <ul>
                  {formatList(data?.acceptance_criteria).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                </ul>
              </div>
              <div className="summary-card">
                <h2>Summary</h2>
                <p>{data?.summary || 'Upload a document to create the summary.'}</p>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'features' && (
          <section className="panel" ref={featuresRef}>
            <div className="panel-header-row">
              <h2>Features to Develop</h2>
              <div className="download-bar">
                <button type="button" className="download-btn" onClick={() => setAddingNew(addingNew === 'feature' ? null : 'feature')}>{addingNew === 'feature' ? 'Cancel' : 'Add'}</button>
                <button type="button" className="download-btn" onClick={() => downloadPdf(featuresRef.current, 'features')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
                <button type="button" className="download-btn" onClick={() => {
                  const headers = ['ID', 'Title', 'Description', 'Dev SP', 'Testing SP', 'Total SP']
                  const rows = localFeatures.map((f) => [
                    f.id, f.title, f.description,
                    localStories.filter((s) => s.feature_id === f.id).reduce((sum, s) => sum + (Number(s.story_points) || 0), 0),
                    featureTestingStoryTotals[f.id] || 0,
                    featureStoryTotals[f.id] || 0,
                  ])
                  downloadExcel(headers, rows, 'features')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/></svg> Excel</button>
                <button type="button" className="download-btn" onClick={() => {
                  const lines = localFeatures.map((f) => {
                    const dev = localStories.filter((s) => s.feature_id === f.id).reduce((sum, s) => sum + (Number(s.story_points) || 0), 0)
                    const test = featureTestingStoryTotals[f.id] || 0
                    const total = featureStoryTotals[f.id] || 0
                    return `${f.id}\t${f.title}\t${f.description}\tDev SP: ${dev}\tTesting SP: ${test}\tTotal SP: ${total}`
                  }).join('\n')
                  downloadTxt(`Features\n\nID\tTitle\tDescription\tDev SP\tTesting SP\tTotal SP\n${lines}`, 'features')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="10" y1="13" x2="14" y2="13"/><line x1="12" y1="11" x2="12" y2="15"/></svg> TXT</button>
                <button type="button" className="download-btn jira-btn" onClick={syncFeaturesToJira} disabled={jiraSyncing || localFeatures.length === 0}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l-5 5 5 5-5 5 5 5 5-5-5-5 5-5z"/></svg>
                  {jiraSyncing ? 'Syncing...' : 'Create in JIRA'}
                </button>
              </div>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Description</th>
                    <th>Dev SP</th>
                    <th>Testing SP</th>
                    <th>Total SP</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {addingNew === 'feature' && (
                    <tr className="editing-row">
                      <td>{nextId('IPMA#', localFeatures)}</td>
                      <td><input type="text" className="edit-input" id="feature-new-title" placeholder="Title" /></td>
                      <td><input type="text" className="edit-input" id="feature-new-desc" placeholder="Description" /></td>
                      <td colSpan="3">-</td>
                      <td>
                        <button type="button" className="download-btn" onClick={() => {
                          const title = document.getElementById('feature-new-title').value.trim()
                          const desc = document.getElementById('feature-new-desc').value.trim()
                          if (!title) return
                          addFeature({ title, description: desc, acceptance_criteria: [] })
                          setAddingNew(null)
                        }}>Save</button>
                      </td>
                    </tr>
                  )}
                  {localFeatures.length === 0 ? (
                    <tr>
                      <td colSpan="7">No feature data yet. Upload an HLDD document to generate the feature backlog.</td>
                    </tr>
                  ) : (
                     localFeatures.map((feature) => (
                      editingFeatureId === feature.id ? (
                        <tr key={feature.id} className="editing-row">
                          <td>{feature.id}</td>
                          <td><input type="text" className="edit-input" defaultValue={feature.title} id={`f-title-${feature.id}`} /></td>
                          <td><input type="text" className="edit-input" defaultValue={feature.description} id={`f-desc-${feature.id}`} /></td>
                          <td>{localStories.filter((s) => s.feature_id === feature.id).reduce((sum, s) => sum + (Number(s.story_points) || 0), 0)}</td>
                          <td>{featureTestingStoryTotals[feature.id] || 0}</td>
                          <td>{featureStoryTotals[feature.id] || 0}</td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => {
                              const title = document.getElementById(`f-title-${feature.id}`).value.trim()
                              const desc = document.getElementById(`f-desc-${feature.id}`).value.trim()
                              if (!title) return
                              updateFeature(feature.id, { title, description: desc })
                              setEditingFeatureId(null)
                            }}>Save</button>
                            <button type="button" className="download-btn" onClick={() => setEditingFeatureId(null)}>Cancel</button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={feature.id}>
                          <td>{feature.id}</td>
                          <td>{feature.title}</td>
                          <td>{feature.description}</td>
                          <td>{localStories.filter((story) => story.feature_id === feature.id).reduce((sum, story) => sum + (Number(story.story_points) || 0), 0)}</td>
                          <td>{featureTestingStoryTotals[feature.id] || 0}</td>
                          <td>{featureStoryTotals[feature.id] || 0}</td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => setEditingFeatureId(feature.id)}>Edit</button>
                            <button type="button" className="download-btn" onClick={() => deleteFeature(feature.id)}>Del</button>
                          </td>
                        </tr>
                      )
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {jiraMessage && (
              <pre className="jira-message">{jiraMessage}</pre>
            )}
          </section>
        )}

        {activeTab === 'stories' && (
          <section className="panel" ref={storiesRef}>
            <div className="panel-header-row">
              <h2>Development Stories</h2>
              <div className="download-bar">
                <button type="button" className="download-btn" onClick={() => setAddingNew(addingNew === 'story' ? null : 'story')}>{addingNew === 'story' ? 'Cancel' : 'Add'}</button>
                <button type="button" className="download-btn" onClick={() => downloadPdf(storiesRef.current, 'stories')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
                <button type="button" className="download-btn" onClick={() => {
                  const headers = ['ID', 'Feature', 'Title', 'Description', 'SP']
                  const rows = localStories.map((s) => [s.id, s.feature_id, s.title, s.description, s.story_points])
                  downloadExcel(headers, rows, 'stories')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/></svg> Excel</button>
                <button type="button" className="download-btn" onClick={() => {
                  const lines = localStories.map((s) => `${s.id}\t${s.feature_id}\t${s.title}\t${s.description}\tSP: ${s.story_points}`).join('\n')
                  downloadTxt(`Development Stories\n\nID\tFeature\tTitle\tDescription\tSP\n${lines}`, 'stories')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="10" y1="13" x2="14" y2="13"/><line x1="12" y1="11" x2="12" y2="15"/></svg> TXT</button>
                <button type="button" className="download-btn jira-btn" onClick={syncStoriesToJira} disabled={jiraStorySyncing || localStories.length === 0 || Object.keys(jiraEpicMapping).length === 0}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l-5 5 5 5-5 5 5 5 5-5-5-5 5-5z"/></svg>
                  {jiraStorySyncing ? 'Syncing...' : 'Create in JIRA'}
                </button>
              </div>
            </div>
            {jiraStoryMessage && (
              <pre className="jira-message">{jiraStoryMessage}</pre>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Feature</th>
                    <th>Title</th>
                    <th>Description</th>
                    <th>SP</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {addingNew === 'story' && (
                    <tr className="editing-row">
                      <td>{nextId('E-CRM#', localStories)}</td>
                      <td>
                        <select className="edit-input" id="story-new-feature">
                          {localFeatures.length ? localFeatures.map((f) => <option key={f.id} value={f.id}>{f.id}</option>) : <option value="">No features</option>}
                        </select>
                      </td>
                      <td><input type="text" className="edit-input" id="story-new-title" placeholder="Title" /></td>
                      <td><input type="text" className="edit-input" id="story-new-desc" placeholder="Description" /></td>
                      <td><input type="number" className="edit-input" id="story-new-sp" defaultValue="1" min="1" max="3" style={{ width: '60px' }} /></td>
                      <td>
                        <button type="button" className="download-btn" onClick={() => {
                          const title = document.getElementById('story-new-title').value.trim()
                          const desc = document.getElementById('story-new-desc').value.trim()
                          const sp = parseInt(document.getElementById('story-new-sp').value, 10) || 1
                          const featureId = document.getElementById('story-new-feature').value
                          if (!title || !featureId) return
                          addStory({ feature_id: featureId, title, description: desc, story_points: Math.min(3, sp), type: 'development' })
                          setAddingNew(null)
                        }}>Save</button>
                      </td>
                    </tr>
                  )}
                  {localStories.length === 0 ? (
                    <tr>
                      <td colSpan="6">No development stories yet. Upload an HLDD document to generate the implementation backlog.</td>
                    </tr>
                  ) : (
                    localStories.map((story) => (
                      editingStoryId === story.id ? (
                        <tr key={story.id} className="editing-row">
                          <td>{story.id}</td>
                          <td>
                            <select className="edit-input" defaultValue={story.feature_id} id={`s-feature-${story.id}`}>
                              {localFeatures.map((f) => <option key={f.id} value={f.id}>{f.id}</option>)}
                            </select>
                          </td>
                          <td><input type="text" className="edit-input" defaultValue={story.title} id={`s-title-${story.id}`} /></td>
                          <td><input type="text" className="edit-input" defaultValue={story.description} id={`s-desc-${story.id}`} /></td>
                          <td><input type="number" className="edit-input" defaultValue={story.story_points} id={`s-sp-${story.id}`} min="1" max="3" style={{ width: '60px' }} /></td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => {
                              const title = document.getElementById(`s-title-${story.id}`).value.trim()
                              const desc = document.getElementById(`s-desc-${story.id}`).value.trim()
                              const sp = parseInt(document.getElementById(`s-sp-${story.id}`).value, 10) || 1
                              const featureId = document.getElementById(`s-feature-${story.id}`).value
                              if (!title) return
                              updateStory(story.id, { feature_id: featureId, title, description: desc, story_points: Math.min(3, sp) })
                              setEditingStoryId(null)
                            }}>Save</button>
                            <button type="button" className="download-btn" onClick={() => setEditingStoryId(null)}>Cancel</button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={story.id}>
                          <td>{story.id}</td>
                          <td>{story.feature_id}</td>
                          <td>{story.title}</td>
                          <td>{story.description}</td>
                          <td>{story.story_points}</td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => setEditingStoryId(story.id)}>Edit</button>
                            <button type="button" className="download-btn" onClick={() => deleteStory(story.id)}>Del</button>
                          </td>
                        </tr>
                      )
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === 'testing' && (
          <section className="panel" ref={testingRef}>
            <div className="panel-header-row">
              <h2>Testing Stories</h2>
              <div className="download-bar">
                <button type="button" className="download-btn" onClick={() => setAddingNew(addingNew === 'testing' ? null : 'testing')}>{addingNew === 'testing' ? 'Cancel' : 'Add'}</button>
                <button type="button" className="download-btn" onClick={() => downloadPdf(testingRef.current, 'testing')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
                <button type="button" className="download-btn" onClick={() => {
                  const headers = ['ID', 'Related Story', 'Title', 'Description', 'SP']
                  const rows = localTestingStories.map((s) => [s.id, s.related_story_id, s.title, s.description, s.story_points])
                  downloadExcel(headers, rows, 'testing')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/></svg> Excel</button>
                <button type="button" className="download-btn" onClick={() => {
                  const lines = localTestingStories.map((s) => `${s.id}\t${s.related_story_id}\t${s.title}\t${s.description}\tSP: ${s.story_points}`).join('\n')
                  downloadTxt(`Testing Stories\n\nID\tRelated Story\tTitle\tDescription\tSP\n${lines}`, 'testing')
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="10" y1="13" x2="14" y2="13"/><line x1="12" y1="11" x2="12" y2="15"/></svg> TXT</button>
                <button type="button" className="download-btn jira-btn" onClick={syncTestingStoriesToJira} disabled={jiraTestingSyncing || localTestingStories.length === 0 || Object.keys(jiraStoryMapping).length === 0}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l-5 5 5 5-5 5 5 5 5-5-5-5 5-5z"/></svg>
                  {jiraTestingSyncing ? 'Syncing...' : 'Create in JIRA'}
                </button>
              </div>
            </div>
            {jiraTestingMessage && (
              <pre className="jira-message">{jiraTestingMessage}</pre>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Related Story</th>
                    <th>Title</th>
                    <th>Description</th>
                    <th>SP</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {addingNew === 'testing' && (
                    <tr className="editing-row">
                      <td>{nextId('TEST-E-CRM#', localTestingStories)}</td>
                      <td>
                        <select className="edit-input" id="test-new-related">
                          {localStories.length ? localStories.map((s) => <option key={s.id} value={s.id}>{s.id}</option>) : <option value="">No stories</option>}
                        </select>
                      </td>
                      <td><input type="text" className="edit-input" id="test-new-title" placeholder="Title" /></td>
                      <td><input type="text" className="edit-input" id="test-new-desc" placeholder="Description" /></td>
                      <td><input type="number" className="edit-input" id="test-new-sp" defaultValue="1" min="1" max="3" style={{ width: '60px' }} /></td>
                      <td>
                        <button type="button" className="download-btn" onClick={() => {
                          const title = document.getElementById('test-new-title').value.trim()
                          const desc = document.getElementById('test-new-desc').value.trim()
                          const sp = parseInt(document.getElementById('test-new-sp').value, 10) || 1
                          const relatedId = document.getElementById('test-new-related').value
                          if (!title || !relatedId) return
                          addTestingStory({ related_story_id: relatedId, title, description: desc, story_points: Math.min(3, sp) })
                          setAddingNew(null)
                        }}>Save</button>
                      </td>
                    </tr>
                  )}
                  {localTestingStories.length === 0 ? (
                    <tr>
                      <td colSpan="6">No testing stories yet. Upload an HLDD document to generate the test backlog.</td>
                    </tr>
                  ) : (
                    localTestingStories.map((story) => (
                      editingTestingId === story.id ? (
                        <tr key={story.id} className="editing-row">
                          <td>{story.id}</td>
                          <td>
                            <select className="edit-input" defaultValue={story.related_story_id} id={`t-related-${story.id}`}>
                              {localStories.map((s) => <option key={s.id} value={s.id}>{s.id}</option>)}
                            </select>
                          </td>
                          <td><input type="text" className="edit-input" defaultValue={story.title} id={`t-title-${story.id}`} /></td>
                          <td><input type="text" className="edit-input" defaultValue={story.description} id={`t-desc-${story.id}`} /></td>
                          <td><input type="number" className="edit-input" defaultValue={story.story_points} id={`t-sp-${story.id}`} min="1" max="3" style={{ width: '60px' }} /></td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => {
                              const title = document.getElementById(`t-title-${story.id}`).value.trim()
                              const desc = document.getElementById(`t-desc-${story.id}`).value.trim()
                              const sp = parseInt(document.getElementById(`t-sp-${story.id}`).value, 10) || 1
                              const relatedId = document.getElementById(`t-related-${story.id}`).value
                              if (!title) return
                              updateTestingStory(story.id, { related_story_id: relatedId, title, description: desc, story_points: Math.min(3, sp) })
                              setEditingTestingId(null)
                            }}>Save</button>
                            <button type="button" className="download-btn" onClick={() => setEditingTestingId(null)}>Cancel</button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={story.id}>
                          <td>{story.id}</td>
                          <td>{story.related_story_id}</td>
                          <td>{story.title}</td>
                          <td>{story.description}</td>
                          <td>{story.story_points}</td>
                          <td className="actions-cell">
                            <button type="button" className="download-btn" onClick={() => setEditingTestingId(story.id)}>Edit</button>
                            <button type="button" className="download-btn" onClick={() => deleteTestingStory(story.id)}>Del</button>
                          </td>
                        </tr>
                      )
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === 'architecture' && (
          <section className="panel" ref={architectureRef}>
            <div className="panel-header-row">
              <h2>Architecture Diagram</h2>
              <div className="download-bar">
                <button type="button" className="download-btn" onClick={() => downloadPdf(architectureRef.current, 'architecture')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
              </div>
            </div>
            {!data ? (
              <p className="note">Upload an HLDD document to generate the architecture diagram.</p>
            ) : (
              <>
                <p className="note">
                  This view mirrors the HLDD workflow. Click the Cloud badge or the cloud platform node to reveal recommended services for the selected platform.
                </p>
                <div className="mermaid-card" style={{ cursor: 'pointer' }} onClick={() => setDiagramModalOpen(true)}>
                  <div ref={mermaidRef} className="mermaid-graph" aria-label="Architecture diagram" />
                </div>
                {diagramModalOpen && (
                  <div className="diagram-modal-overlay" onClick={() => setDiagramModalOpen(false)}>
                    <div className="diagram-modal-content" onClick={(e) => e.stopPropagation()}>
                      <button type="button" className="diagram-modal-close" onClick={() => setDiagramModalOpen(false)}>Close</button>
                      <div className="diagram-modal-graph" ref={modalMermaidRef} />
                    </div>
                  </div>
                )}
                <div className="legend-stack">
                  {legendLabels.map((legend) => {
                    const isCloudLegend = legend.key === 'cloud'
                    const isCloudActive = isCloudLegend && showCloudExpanded
                    const isClickable = isCloudLegend && hasCloudExpansion
                    const isExpanded = expandedLegends[legend.key]

                    if (isCloudLegend) {
                      return (
                        <button
                          key={legend.key}
                          type="button"
                          className={`legend-pill ${legend.key}-pill ${isCloudActive ? 'legend-pill-active' : ''} ${isClickable ? 'legend-pill-clickable' : ''}`}
                          onClick={handleCloudToggle}
                          disabled={!isClickable}
                          aria-pressed={isCloudActive}
                          title={isClickable ? `Expand ${legend.label} recommendations` : `${legend.label} recommendations are not available`}
                        >
                          {isCloudActive ? `${legend.label} • Expanded` : legend.label}
                        </button>
                      )
                    }

                    return (
                      <button
                        key={legend.key}
                        type="button"
                        className={`legend-pill ${legend.key}-pill legend-pill-clickable ${isExpanded ? 'legend-pill-active' : ''}`}
                        onClick={() => handleLegendToggle(legend.key)}
                        aria-pressed={isExpanded}
                        title="Click for details"
                      >
                        {legend.label}
                      </button>
                    )
                  })}
                </div>
                {legendLabels.some((l) => expandedLegends[l.key] && l.key !== 'cloud') && (
                  <div className="legend-details">
                    {legendLabels.map((legend) => {
                      if (!expandedLegends[legend.key] || legend.key === 'cloud') return null
                      return (
                        <div key={legend.key} className="legend-detail-card">
                          <strong className="legend-detail-header">{legend.label}</strong>
                          {legend.nodes.map((node) => (
                            <p key={node.id} className="legend-detail-text">
                              <span className="legend-detail-node">{node.label}:</span> {node.detail}
                            </p>
                          ))}
                        </div>
                      )
                    })}
                  </div>
                )}
                <p className="legend-note">
                  {showCloudExpanded ? 'Expanded cloud services are shown below.' : 'Click the cloud badge or the cloud platform node to reveal probable services for the selected platform.'}
                </p>
                {showCloudExpanded && cloudServices.length > 0 && (
                  <div className="cloud-services-panel">
                    <div className="cloud-services-header">
                      <div>
                        <strong>Recommended services</strong>
                        <p className="cloud-summary-copy">{cloudRecommendationSummary}</p>
                      </div>
                      <span>{cloudServices.length} probable services</span>
                    </div>
                    <div className="cloud-service-groups">
                      {['Primary', 'Secondary', 'Optional'].map((tier) => {
                        const tierServices = cloudServicesByTier[tier] || []

                        if (!tierServices.length) {
                          return null
                        }

                        return (
                          <div key={tier} className={`cloud-service-group cloud-service-group-${tier.toLowerCase()}`}>
                            <div className="cloud-service-group-header">
                              <strong>{tier}</strong>
                              <span>{tierServices.length} service{tierServices.length === 1 ? '' : 's'}</span>
                            </div>
                            <div className="cloud-services-list">
                              {tierServices.map((service) => {
                                const meta = cloudServiceMeta[service] || {
                                  icon: '☁️',
                                  description: 'Recommended cloud service for the selected platform.',
                                  tier: 'Optional',
                                  summary: 'Recommended to align the operating model with the selected cloud platform.',
                                }

                                return (
                                  <div
                                    key={service}
                                    className={`cloud-service-item cloud-service-item-tier-${meta.tier.toLowerCase()}`}
                                    title={meta.summary}
                                  >
                                    <span className="cloud-service-icon">{meta.icon}</span>
                                    <div className="cloud-service-copy">
                                      <div className="cloud-service-title-row">
                                        <span className="cloud-service-name">{service}</span>
                                        <span className="cloud-service-status">{meta.tier}</span>
                                      </div>
                                      <span className="cloud-service-description">{meta.description}</span>
                                      <span className="cloud-service-summary">Why this recommendation: {meta.summary}</span>
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
                <div className="edge-list">
                  {architectureEdges.map((edge) => (
                    <div key={`${edge.from}-${edge.to}`} className="edge-pill">
                      <span>{edge.from}</span>
                      <strong>{edge.label}</strong>
                      <span>{edge.to}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>
        )}

        {activeTab === 'structure' && (
          <section className="panel structure-panel" ref={structureRef}>
            <div className="structure-panel-header">
              <div>
                <h2>Proposed Project Structure</h2>
                <p className="note">
                  The structure is derived from the uploaded HLDD technology stack and project management tool inputs.
                </p>
              </div>
              <div className="download-bar">
                <button type="button" className="download-btn" onClick={() => downloadPdf(structureRef.current, 'project-structure')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg> PDF</button>
                <button type="button" className="download-btn" onClick={async () => {
                  const structure = data?.project_structure || []
                  if (!structure.length) return
                  try {
                    const res = await fetch('http://localhost:8000/api/download/structure', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ project_structure: structure }),
                    })
                    if (!res.ok) throw new Error('Download failed')
                    const blob = await res.blob()
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = 'project-structure.zip'
                    document.body.appendChild(a)
                    a.click()
                    document.body.removeChild(a)
                    URL.revokeObjectURL(url)
                  } catch (e) {
                    console.error('Structure download error:', e)
                  }
                }}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> ZIP</button>
              </div>
              <div className="structure-summary">
                <div className="structure-stat">
                  <span>Top-level entries</span>
                  <strong>{structureSummary.topLevel}</strong>
                </div>
                <div className="structure-stat">
                  <span>Directories</span>
                  <strong>{structureSummary.directories}</strong>
                </div>
                <div className="structure-stat">
                  <span>Files</span>
                  <strong>{structureSummary.files}</strong>
                </div>
              </div>
            </div>
            <div className="structure-layout">
              <div className="structure-tree-card">
                <ul className="structure-tree">
                  <ProjectTreeNode node={projectStructureTree} />
                </ul>
              </div>
              <div className="structure-overview-card">
                <h3>Quick overview</h3>
                <ul className="structure-overview-list">
                  {projectStructureTree.children.map((child) => (
                    <li key={child.name} className="structure-overview-item">
                      <span>{child.isDirectory ? '📁' : '📄'}</span>
                      <strong>{child.name}</strong>
                      <span>{child.isDirectory ? 'folder' : 'file'}</span>
                    </li>
                  ))}
                </ul>
                <p className="note">
                  Use the directory tree to scan the generated layout and the quick overview to confirm the top-level repository shape.
                </p>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'chatbot' && (
          <section className="panel chatbot-panel">
            <div className="chatbot-header">
              <svg className="chatbot-ai-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <defs>
                  <linearGradient id="robo-grad" x1="4" y1="4" x2="48" y2="48">
                    <stop offset="0%" stopColor="#38bdf8"/>
                    <stop offset="50%" stopColor="#818cf8"/>
                    <stop offset="100%" stopColor="#c084fc"/>
                  </linearGradient>
                </defs>
                <path d="M26 6C16 6 8 13 8 22c0 5 2.5 9.5 6.5 12.5L12 44l10.5-6c1 .3 2 .5 3.5.5 10 0 18-7 18-16.5S36 6 26 6z" stroke="url(#robo-grad)" strokeWidth="1.6" fill="rgba(56,189,248,0.04)"/>
                <path d="M18 20h16M18 26h12M18 14h14" stroke="url(#robo-grad)" strokeWidth="1.6" strokeLinecap="round"/>
              </svg>
              <div>
                <h2>Chatbot Agent</h2>
                <p className="note">
                  This tab references the uploaded HLDD context and suggests the best-fit model for the current stack. You can ask for project functionality, frontend/backend/cloud alternatives, cost breakdowns, and the tradeoffs around efficiency, security, and turnaround time.
                </p>
              </div>
            </div>
            <div className="panel-grid chatbot-grid">
              <div className="summary-card highlight">
                <h3>Recommended LLM</h3>
                <p><strong>{recommendedLLM.provider}</strong> — {recommendedLLM.model}</p>
                <p>{recommendedLLM.reason}</p>
              </div>
              <div className="summary-card">
                <h3>Reference context</h3>
                <ul>
                  <li>{data?.title || 'No uploaded title yet'}</li>
                  <li>{data?.project_management_tool || 'Project management tool not provided'}</li>
                  <li>{data?.repository || 'Repository not provided'}</li>
                  <li>{data?.ci_cd_pipeline || 'CI/CD pipeline not provided'}</li>
                  <li>{(data?.technology_stack || []).length ? data.technology_stack.join(', ') : 'No stack selected yet'}</li>
                  <li>{localFeatures.length} feature{localFeatures.length === 1 ? '' : 's'} derived from the HLDD</li>
                </ul>
              </div>
            </div>

            <div className="chatbot-suggested-prompts">
              <h3>Suggested prompts</h3>
              <div className="prompt-pills">
                {chatbotPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="prompt-pill"
                    onClick={() => setChatbotPrompt(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            <div className="chatbot-input-card">
              <label htmlFor="chatbot-priority" className="field-label">Recommendation priority</label>
              <select
                id="chatbot-priority"
                value={chatbotPriority}
                onChange={(event) => setChatbotPriority(event.target.value)}
              >
                <option value="balanced">Balanced</option>
                <option value="lowest cost">Lowest cost</option>
                <option value="fastest time to market">Fastest time to market</option>
                <option value="highest security">Highest security</option>
              </select>
              <label htmlFor="chatbot-prompt" className="field-label">Ask the agent</label>
              <textarea
                id="chatbot-prompt"
                className="chatbot-textarea"
                rows="5"
                value={chatbotPrompt}
                onChange={(event) => setChatbotPrompt(event.target.value)}
                placeholder="Ask about functionality, preferred framework, alternate frontend/backend/cloud options, cost, security, efficiency, or turnaround time."
              />
              <div className="chatbot-actions">
                <button type="button" onClick={handleChatbotGenerate} disabled={chatbotLoading || !data}>
                  {chatbotLoading ? (
                    <span className="chatbot-loading-btn">
                      Generating
                      <span className="chatbot-loading-dots"><span></span><span></span><span></span></span>
                    </span>
                  ) : 'Generate response'}
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setChatbotPrompt('')
                    setChatbotPriority('balanced')
                    setChatbotResponse('')
                    setChatbotError('')
                  }}
                >
                  Clear
                </button>
              </div>
              {chatbotError && <p className="note">{chatbotError}</p>}
              {chatbotResponse && (
                <div className="chatbot-response">
                  <h3>Generated response</h3>
                  <pre>{chatbotResponse}</pre>
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === 'agent' && (
          <section className="panel chatbot-panel" style={{maxWidth: 900, margin: '0 auto'}}>
            <div className="chatbot-header">
              <svg className="chatbot-ai-icon" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <defs>
                  <linearGradient id="agent-grad" x1="4" y1="4" x2="48" y2="48">
                    <stop offset="0%" stopColor="#f59e0b"/>
                    <stop offset="50%" stopColor="#ef4444"/>
                    <stop offset="100%" stopColor="#ec4899"/>
                  </linearGradient>
                </defs>
                <rect x="10" y="16" width="32" height="20" rx="4" stroke="url(#agent-grad)" strokeWidth="1.6" fill="rgba(245,158,11,0.04)"/>
                <circle cx="26" cy="10" r="4" stroke="url(#agent-grad)" strokeWidth="1.6" fill="rgba(245,158,11,0.04)"/>
                <line x1="26" y1="14" x2="26" y2="18" stroke="url(#agent-grad)" strokeWidth="1.6" strokeLinecap="round"/>
                <line x1="20" y1="23" x2="32" y2="23" stroke="url(#agent-grad)" strokeWidth="1.6" strokeLinecap="round"/>
                <line x1="20" y1="29" x2="28" y2="29" stroke="url(#agent-grad)" strokeWidth="1.6" strokeLinecap="round"/>
              </svg>
              <div>
                <h2>Agentic AI</h2>
                <p className="note">
                  The LangGraph agent can parse HLDD documents, generate project plans, answer questions via Gemini,
                  create JIRA Epics/Stories/Subtasks, and execute multi-step workflows autonomously. It uses
                  <strong> Groq (llama-3.1-8b-instant)</strong> as its default LLM with Gemini fallback.
                </p>
              </div>
            </div>

            <div className="chatbot-suggested-prompts">
              <h3>Suggested prompts</h3>
              <div className="prompt-pills">
                {agentPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="prompt-pill"
                    onClick={() => setAgentInput(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>

            {agentJiraPending && (
              <div style={{padding: 16, background: 'linear-gradient(135deg, #1e293b, #0f172a)', borderRadius: 12, border: '1px solid #f59e0b', marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center'}}>
                <p style={{margin: 0, color: '#fbbf24', fontWeight: 600, fontSize: '0.95rem'}}>
                  ⚠️ JIRA Creation Pending Approval
                </p>
                <p style={{margin: 0, color: '#cbd5e1', fontSize: '0.85rem', textAlign: 'center'}}>
                  The agent wants to create Epics, Stories, and Subtasks in JIRA.<br />
                  Review the plan above and approve or deny.
                </p>
                <div style={{display: 'flex', gap: 10}}>
                  <button
                    type="button"
                    style={{background: '#22c55e', color: '#052e16', border: 'none', padding: '8px 24px', borderRadius: 8, fontWeight: 600, cursor: 'pointer'}}
                    onClick={handleJiraApprove}
                    disabled={agentJiraConfirming}
                  >
                    {agentJiraConfirming ? 'Creating...' : '✅ Approve'}
                  </button>
                  <button
                    type="button"
                    style={{background: '#ef4444', color: '#fff', border: 'none', padding: '8px 24px', borderRadius: 8, fontWeight: 600, cursor: 'pointer'}}
                    onClick={handleJiraDeny}
                    disabled={agentJiraConfirming}
                  >
                    ❌ Deny
                  </button>
                </div>
              </div>
            )}
            <div className="chat-messages" style={{maxHeight: 400, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, padding: 12, background: '#0f172a', borderRadius: 12, border: '1px solid #334155'}}>
              {agentMessages.length === 0 && (
                <div className="chat-messages-empty">
                  <p>Send a message to start a conversation with the agent. Upload an HLDD file or just ask a question.</p>
                </div>
              )}
              {agentMessages.map((msg, i) => (
                <div key={i} className={`chat-message ${msg.role}`}>
                  <span className="sender-label">{msg.role === 'user' ? 'You' : 'Agent'}</span>
                  <div className="bubble"><p style={{whiteSpace: 'pre-wrap', margin: 0}}>{msg.content}</p></div>
                </div>
              ))}
              {agentLoading && (
                <div className="chat-message agent">
                  <span className="sender-label">Agent</span>
                  <div className="bubble">
                    <p style={{margin: 0}}>
                      Thinking<span className="chatbot-loading-dots"><span></span><span></span><span></span></span>
                    </p>
                  </div>
                </div>
              )}
            </div>

            {agentFile && (
              <p className="note" style={{color: '#fbbf24'}}>Attached: {agentFile.name}</p>
            )}

            <div style={{display: 'flex', flexDirection: 'column', gap: 10}}>
              <label className="field-label" style={{fontSize: '0.82rem', color: '#94a3b8'}}>
                Upload HLDD file (optional)
                <input
                  type="file"
                  accept=".txt,.md,.docx,.pdf"
                  onChange={handleAgentFileChange}
                  style={{marginLeft: 10, color: '#cbd5e1', fontSize: '0.82rem'}}
                />
              </label>
              <div className="chat-input-row">
                <textarea
                  value={agentInput}
                  onChange={(e) => setAgentInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAgentSend(); } }}
                  placeholder="Ask the agent to parse HLDD, generate plans, answer questions, or create JIRA items..."
                  rows="2"
                />
                <button
                  type="button"
                  className="chat-send-btn"
                  onClick={handleAgentSend}
                  disabled={agentLoading || (!agentInput.trim() && !agentFileText)}
                >
                  {agentLoading ? '...' : 'Send'}
                </button>
              </div>

              <button
                type="button"
                className="secondary-button"
                style={{alignSelf: 'flex-start'}}
                onClick={() => {
                  setAgentMessages([])
                  setAgentInput('')
                  setAgentError('')
                  setAgentContext(null)
                  setAgentFile(null)
                  setAgentFileText('')
                  setAgentJiraPending(null)
                  setAgentJiraConfirming(false)
                }}
              >
                Clear conversation
              </button>
            </div>

            {agentError && <p className="note" style={{color: '#f87171', marginTop: 8}}>{agentError}</p>}
          </section>
        )}
      </main>
    </div>
  )
}
