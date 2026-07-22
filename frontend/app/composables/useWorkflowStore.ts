/**
 * Workflow Store Composable
 *
 * Persists named workflows so users do not lose their graph on reload.
 * Backed by localStorage today; the API surface is shaped so it can swap
 * to a backend store (`/workflows` routes) without changing callers.
 */

import type { WorkflowNode } from './useJourney'

export interface SavedWorkflow {
  id: string
  name: string
  description?: string
  nodes: WorkflowNode[]
  createdAt: number
  updatedAt: number
}

const STORAGE_KEY = 'dr-vision.workflows.v1'

function readAll(): SavedWorkflow[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (err) {
    console.warn('Failed to parse saved workflows', err)
    return []
  }
}

function writeAll(items: SavedWorkflow[]): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch (err) {
    console.error('Failed to persist workflows', err)
  }
}

function genId(): string {
  return `wf-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * Strip non-serialisable runtime state before storing.
 *
 * `File` objects (upload nodes) cannot be JSON-serialised and are not
 * expected to round-trip; the user re-selects files on load.
 */
function sanitizeNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  return nodes.map((n) => {
    const { files, result, status, ...rest } = n
    return {
      ...rest,
      // reset transient state
      status: 'pending',
      // omit File objects entirely
      files: n.type === 'upload' ? [] : undefined,
    } as WorkflowNode
  })
}

export function useWorkflowStore() {
  const workflows = useState<SavedWorkflow[]>('workflow-store', () => readAll())

  const refresh = () => {
    workflows.value = readAll()
  }

  const list = (): SavedWorkflow[] => {
    return [...workflows.value].sort((a, b) => b.updatedAt - a.updatedAt)
  }

  const get = (id: string): SavedWorkflow | undefined => {
    return workflows.value.find((w) => w.id === id)
  }

  const save = (name: string, nodes: WorkflowNode[], description?: string): SavedWorkflow => {
    const now = Date.now()
    const wf: SavedWorkflow = {
      id: genId(),
      name: name.trim() || 'Untitled workflow',
      description,
      nodes: sanitizeNodes(nodes),
      createdAt: now,
      updatedAt: now,
    }
    const all = readAll()
    all.push(wf)
    writeAll(all)
    workflows.value = all
    return wf
  }

  const update = (id: string, patch: Partial<Pick<SavedWorkflow, 'name' | 'description' | 'nodes'>>): SavedWorkflow | undefined => {
    const all = readAll()
    const idx = all.findIndex((w) => w.id === id)
    if (idx === -1) return undefined
    const current = all[idx]!
    const next: SavedWorkflow = {
      ...current,
      ...patch,
      nodes: patch.nodes ? sanitizeNodes(patch.nodes) : current.nodes,
      updatedAt: Date.now(),
    }
    all[idx] = next
    writeAll(all)
    workflows.value = all
    return next
  }

  const remove = (id: string): boolean => {
    const all = readAll()
    const next = all.filter((w) => w.id !== id)
    if (next.length === all.length) return false
    writeAll(next)
    workflows.value = next
    return true
  }

  const clear = (): void => {
    writeAll([])
    workflows.value = []
  }

  return {
    workflows,
    refresh,
    list,
    get,
    save,
    update,
    remove,
    clear,
  }
}
