/**
 * useApiExplorer Composable
 * Quản lý state và logic gọi API cho trang API Explorer.
 */

export interface ApiField {
  name: string
  type: 'text' | 'textarea' | 'file' | 'checkbox' | 'select' | 'number'
  required: boolean
  label: string
  placeholder?: string
  default?: string | boolean | number
  options?: string[]
  accept?: string
  path_param?: boolean
}

export interface ApiEndpoint {
  id: string
  group: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  summary: string
  description: string
  fields: ApiField[]
}

export interface ApiGroup {
  name: string
  endpoints: ApiEndpoint[]
}

export interface ApiResponse {
  status: number
  data: any
  duration: number
  error?: string
}

export function useApiExplorer() {
  const config = useRuntimeConfig()
  const apiBaseUrl = config.public.apiBaseUrl as string

  const endpoints = ref<ApiEndpoint[]>([])
  const groups = ref<ApiGroup[]>([])
  const isLoadingEndpoints = ref(false)
  const selectedEndpoint = ref<ApiEndpoint | null>(null)
  const fieldValues = ref<Record<string, any>>({})
  const fileValues = ref<Record<string, File | null>>({})
  const isExecuting = ref(false)
  const response = ref<ApiResponse | null>(null)
  const curlCommand = ref('')

  /**
   * Tải danh sách endpoint từ backend
   */
  const loadEndpoints = async () => {
    isLoadingEndpoints.value = true
    try {
      const result = await $fetch<{ success: boolean; groups: ApiGroup[]; endpoints: ApiEndpoint[] }>(
        `${apiBaseUrl}/api-explorer/endpoints`
      )
      endpoints.value = result.endpoints
      groups.value = result.groups
    } catch (e: any) {
      console.error('Không thể tải danh sách endpoint:', e)
    } finally {
      isLoadingEndpoints.value = false
    }
  }

  /**
   * Chọn endpoint và khởi tạo giá trị mặc định
   */
  const selectEndpoint = (ep: ApiEndpoint) => {
    selectedEndpoint.value = ep
    response.value = null
    curlCommand.value = ''

    // Reset values
    const vals: Record<string, any> = {}
    const files: Record<string, File | null> = {}

    for (const field of ep.fields) {
      if (field.type === 'file') {
        files[field.name] = null
      } else if (field.type === 'checkbox') {
        vals[field.name] = field.default ?? false
      } else if (field.type === 'select') {
        vals[field.name] = field.default ?? (field.options?.[0] ?? '')
      } else {
        vals[field.name] = field.default ?? ''
      }
    }

    fieldValues.value = vals
    fileValues.value = files
    updateCurl()
  }

  /**
   * Xây dựng URL thực tế (thay path params)
   */
  const buildUrl = (): string => {
    if (!selectedEndpoint.value) return ''
    let path = selectedEndpoint.value.path
    for (const field of selectedEndpoint.value.fields) {
      if (field.path_param && fieldValues.value[field.name]) {
        path = path.replace(`{${field.name}}`, encodeURIComponent(fieldValues.value[field.name]))
      }
    }
    return `${apiBaseUrl}${path}`
  }

  /**
   * Tạo lệnh curl tương ứng
   */
  const updateCurl = () => {
    if (!selectedEndpoint.value) return
    const ep = selectedEndpoint.value
    let url = buildUrl()
    const method = ep.method

    if (method === 'GET') {
      curlCommand.value = `curl -X GET "${url}"`
      return
    }

    // POST với form data
    const parts: string[] = [`curl -X POST "${url}"`]
    for (const field of ep.fields) {
      if (field.path_param) continue
      if (field.type === 'file') {
        parts.push(`  -F "${field.name}=@/path/to/file"`)
      } else if (field.type === 'checkbox') {
        parts.push(`  -F "${field.name}=${fieldValues.value[field.name] ?? field.default ?? false}"`)
      } else {
        const val = fieldValues.value[field.name]
        if (val !== undefined && val !== '') {
          parts.push(`  -F "${field.name}=${val}"`)
        }
      }
    }
    curlCommand.value = parts.join(' \\\n')
  }

  /**
   * Thực thi API call
   */
  const execute = async () => {
    if (!selectedEndpoint.value) return
    const ep = selectedEndpoint.value
    isExecuting.value = true
    response.value = null

    const start = Date.now()
    try {
      const url = buildUrl()

      if (ep.method === 'GET') {
        const data = await $fetch(url)
        response.value = { status: 200, data, duration: Date.now() - start }
      } else {
        // POST với FormData
        const formData = new FormData()
        for (const field of ep.fields) {
          if (field.path_param) continue
          if (field.type === 'file') {
            const f = fileValues.value[field.name]
            if (f) formData.append(field.name, f)
          } else {
            const val = fieldValues.value[field.name]
            if (val !== undefined && val !== '') {
              formData.append(field.name, String(val))
            }
          }
        }

        const data = await $fetch(url, { method: 'POST', body: formData })
        response.value = { status: 200, data, duration: Date.now() - start }
      }
    } catch (e: any) {
      const status = e?.response?.status ?? e?.statusCode ?? 500
      const errData = e?.data ?? e?.response?._data ?? { detail: e?.message ?? 'Lỗi không xác định' }
      response.value = {
        status,
        data: errData,
        duration: Date.now() - start,
        error: errData?.detail ?? String(e),
      }
    } finally {
      isExecuting.value = false
    }
  }

  /**
   * Sao chép curl vào clipboard
   */
  const copyCurl = async () => {
    if (!curlCommand.value) return
    await navigator.clipboard.writeText(curlCommand.value)
  }

  /**
   * Sao chép response vào clipboard
   */
  const copyResponse = async () => {
    if (!response.value) return
    await navigator.clipboard.writeText(JSON.stringify(response.value.data, null, 2))
  }

  // Màu theo method
  const methodColor = (method: string) => {
    const map: Record<string, string> = {
      GET: 'text-emerald-400 bg-emerald-400/10',
      POST: 'text-blue-400 bg-blue-400/10',
      PUT: 'text-amber-400 bg-amber-400/10',
      DELETE: 'text-red-400 bg-red-400/10',
    }
    return map[method] ?? 'text-gray-400 bg-gray-400/10'
  }

  // Màu status code
  const statusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-emerald-400'
    if (status >= 400 && status < 500) return 'text-amber-400'
    return 'text-red-400'
  }

  return {
    endpoints,
    groups,
    isLoadingEndpoints,
    selectedEndpoint,
    fieldValues,
    fileValues,
    isExecuting,
    response,
    curlCommand,
    loadEndpoints,
    selectEndpoint,
    updateCurl,
    execute,
    copyCurl,
    copyResponse,
    methodColor,
    statusColor,
  }
}
