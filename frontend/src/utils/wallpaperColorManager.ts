/**
 * 图片颜色提取工具
 * 从图片中提取主要颜色用于主题色
 */

interface RGB {
  r: number
  g: number
  b: number
}

/**
 * 将 RGB 颜色转换为十六进制字符串
 */
function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')}`
}

/**
 * 计算颜色的亮度
 */
function getLuminance(r: number, g: number, b: number): number {
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255
}

/**
 * 计算两个颜色之间的距离
 */
function colorDistance(c1: RGB, c2: RGB): number {
  const rDiff = c1.r - c2.r
  const gDiff = c1.g - c2.g
  const bDiff = c1.b - c2.b
  return Math.sqrt(rDiff * rDiff + gDiff * gDiff + bDiff * bDiff)
}

/**
 * 简化的 K-means 聚类提取主要颜色
 */
function kMeansClustering(pixels: RGB[], k: number, maxIterations = 10): RGB[] {
  if (pixels.length === 0) return []
  
  // 随机初始化聚类中心
  let centroids: RGB[] = []
  const step = Math.floor(pixels.length / k)
  for (let i = 0; i < k; i++) {
    centroids.push({ ...pixels[Math.min(i * step, pixels.length - 1)] })
  }

  for (let iter = 0; iter < maxIterations; iter++) {
    // 分配像素到最近的聚类中心
    const clusters: RGB[][] = Array.from({ length: k }, () => [])
    
    for (const pixel of pixels) {
      let minDist = Infinity
      let clusterIndex = 0
      
      for (let i = 0; i < k; i++) {
        const dist = colorDistance(pixel, centroids[i])
        if (dist < minDist) {
          minDist = dist
          clusterIndex = i
        }
      }
      
      clusters[clusterIndex].push(pixel)
    }

    // 更新聚类中心
    let changed = false
    for (let i = 0; i < k; i++) {
      if (clusters[i].length === 0) continue
      
      const newCentroid = {
        r: Math.round(clusters[i].reduce((sum, p) => sum + p.r, 0) / clusters[i].length),
        g: Math.round(clusters[i].reduce((sum, p) => sum + p.g, 0) / clusters[i].length),
        b: Math.round(clusters[i].reduce((sum, p) => sum + p.b, 0) / clusters[i].length),
      }
      
      if (colorDistance(newCentroid, centroids[i]) > 1) {
        changed = true
      }
      centroids[i] = newCentroid
    }
    
    if (!changed) break
  }

  return centroids
}

/**
 * 从图片文件中提取主要颜色
 * @param file 图片文件
 * @param colorCount 需要提取的颜色数量
 * @returns 颜色十六进制数组
 */
export async function extractColorsFromImage(
  file: File,
  colorCount: number = 6
): Promise<string[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = (e) => {
      const img = new Image()

      img.onload = () => {
        try {
          // 创建 canvas 并设置尺寸
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          if (!ctx) {
            reject(new Error('无法获取 canvas 上下文'))
            return
          }

          // 缩小图片以提高性能
          const maxSize = 200
          const scale = Math.min(maxSize / img.width, maxSize / img.height, 1)
          canvas.width = img.width * scale
          canvas.height = img.height * scale

          // 绘制图片
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

          // 获取像素数据
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const pixels: RGB[] = []

          // 采样像素（每隔几个像素取一个）
          const samplingRate = 4
          for (let i = 0; i < imageData.data.length; i += 4 * samplingRate) {
            const r = imageData.data[i]
            const g = imageData.data[i + 1]
            const b = imageData.data[i + 2]
            const a = imageData.data[i + 3]

            // 跳过透明和过于极端的颜色
            if (a < 128) continue
            const luminance = getLuminance(r, g, b)
            if (luminance < 0.1 || luminance > 0.9) continue

            pixels.push({ r, g, b })
          }

          if (pixels.length < colorCount) {
            reject(new Error('图片颜色数量不足'))
            return
          }

          // 使用 K-means 提取主要颜色
          const mainColors = kMeansClustering(pixels, colorCount)

          // 按饱和度和亮度排序，优先选择鲜艳的颜色
          const sortedColors = mainColors
            .map(color => {
              const max = Math.max(color.r, color.g, color.b)
              const min = Math.min(color.r, color.g, color.b)
              const saturation = max === 0 ? 0 : (max - min) / max
              const luminance = getLuminance(color.r, color.g, color.b)
              // 偏好中等亮度和高饱和度
              const score = saturation * (1 - Math.abs(luminance - 0.5))
              return { color, score }
            })
            .sort((a, b) => b.score - a.score)
            .map(item => rgbToHex(item.color.r, item.color.g, item.color.b))

          resolve(sortedColors)
        } catch (error) {
          reject(error)
        }
      }

      img.onerror = () => {
        reject(new Error('图片加载失败'))
      }

      img.src = e.target?.result as string
    }

    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }

    reader.readAsDataURL(file)
  })
}

/**
 * localStorage 键名
 */
const WALLPAPER_COLORS_KEY = 'mofox_wallpaper_colors'

/**
 * 保存壁纸取色结果到 localStorage
 */
export function saveWallpaperColors(colors: string[]): void {
  try {
    localStorage.setItem(WALLPAPER_COLORS_KEY, JSON.stringify(colors))
  } catch (error) {
    console.error('保存壁纸颜色失败:', error)
  }
}

/**
 * 从 localStorage 加载壁纸取色结果
 */
export function loadWallpaperColors(): string[] | null {
  try {
    const stored = localStorage.getItem(WALLPAPER_COLORS_KEY)
    if (!stored) return null
    const colors = JSON.parse(stored)
    return Array.isArray(colors) ? colors : null
  } catch (error) {
    console.error('加载壁纸颜色失败:', error)
    return null
  }
}

/**
 * 清除 localStorage 中的壁纸颜色
 */
export function clearWallpaperColors(): void {
  try {
    localStorage.removeItem(WALLPAPER_COLORS_KEY)
  } catch (error) {
    console.error('清除壁纸颜色失败:', error)
  }
}
