<template>
  <button
    type="button"
    :class="[
      'relative inline-flex h-8 w-16 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2',
      modelValue ? 'bg-[#ff4f00] focus:ring-ds-orange' : 'bg-sand focus:ring-ds-gray'
    ]"
    @click="toggle"
  >
    <span class="sr-only">{{ label }}</span>
    <span
      :class="[
        'inline-block h-6 w-6 transform rounded-full bg-cream shadow-lg ring-0 transition-transform duration-200 ease-in-out',
        modelValue ? 'translate-x-9' : 'translate-x-1'
      ]"
    >
      <span
        v-if="modelValue"
        class="flex h-full w-full items-center justify-center"
      >
        <svg class="h-3 w-3 text-ds-orange" fill="currentColor" viewBox="0 0 12 12">
          <path d="M3.707 5.293a1 1 0 00-1.414 1.414l1.414-1.414zM5 8l-.707.707a1 1 0 001.414 0L5 8zm4.707-3.293a1 1 0 00-1.414-1.414l1.414 1.414zm-7.414 2l2 2 1.414-1.414-2-2-1.414 1.414zm3.414 2l4-4-1.414-1.414-4 4 1.414 1.414z" />
        </svg>
      </span>
      <span
        v-else
        class="flex h-full w-full items-center justify-center"
      >
        <svg class="h-3 w-3 text-ds-gray" fill="currentColor" viewBox="0 0 12 12">
          <path d="M4 8l2-2m0 0l2-2M6 6L4 4m2 2l2 2" />
        </svg>
      </span>
    </span>
  </button>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Toggle'
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const toggle = () => {
  emit('update:modelValue', !props.modelValue)
}
</script>
