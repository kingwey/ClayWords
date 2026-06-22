/**
 * 设计方案版本树
 *
 * 从 DesignView.vue 抽出：
 * - versions：累积的版本快照（釉色、颜色、描述、tags、时间戳）
 * - pushVersion：当前方案 → 新版本快照
 * - rollbackToVersion：回滚到某版本，并自动追加一条"回滚"记录
 *
 * 使用方式：
 *   const { versions, pushVersion, rollbackToVersion } = useDesignVersions(currentOption)
 */
import { ref, type Ref } from 'vue'

export interface OptionColors {
  light: string
  mid: string
  dark: string
}

export interface VersionedOption {
  glaze: string
  colors: OptionColors
  desc: string
  tags: string[]
}

export interface DesignVersion {
  versionNo: number
  label: string
  glaze: string
  colors: OptionColors
  desc: string
  tagsSnapshot: string[]
  createdAt: number
}

export function useDesignVersions(
  currentOption: Ref<VersionedOption | null>,
  onAfterRollback?: (v: DesignVersion) => void,
) {
  const versions = ref<DesignVersion[]>([])
  const showVersionTree = ref(false)

  function pushVersion(label: string) {
    const opt = currentOption.value
    if (!opt) return
    versions.value.push({
      versionNo: versions.value.length + 1,
      label,
      glaze: opt.glaze,
      colors: { ...opt.colors },
      desc: opt.desc,
      tagsSnapshot: [...opt.tags],
      createdAt: Date.now(),
    })
  }

  function rollbackToVersion(v: DesignVersion) {
    const opt = currentOption.value
    if (!opt) return
    opt.glaze = v.glaze
    opt.colors = { ...v.colors }
    opt.desc = v.desc
    opt.tags = [...v.tagsSnapshot]

    // 在最末追加一条"回滚"记录
    versions.value.push({
      ...v,
      versionNo: versions.value.length + 1,
      label: `回滚到 v${v.versionNo}：${v.label}`,
      createdAt: Date.now(),
    })

    // 调用方副作用：例如同步全局 currentGlaze 或强制响应式刷新
    onAfterRollback?.(v)
  }

  return {
    versions,
    showVersionTree,
    pushVersion,
    rollbackToVersion,
  }
}
