/**
 * 视频帧提取工具
 * 从视频文件中提取第一帧作为图片，用于取色分析
 */

/**
 * 从视频文件中提取第一帧
 * @param file 视频文件
 * @param timeOffset 提取帧的时间偏移（秒），默认 0.1 秒避免黑屏
 * @returns 第一帧的 Blob 对象（JPEG 格式）
 */
export async function extractFirstFrameFromVideo(
  file: File,
  timeOffset: number = 0.1
): Promise<Blob> {
  console.log('[视频帧提取] 开始提取第一帧:', {
    fileName: file.name,
    fileSize: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
    fileType: file.type,
    timeOffset
  })
  
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')

    if (!ctx) {
      console.error('[视频帧提取] 无法获取 canvas 上下文')
      reject(new Error('无法获取 canvas 上下文'))
      return
    }

    video.preload = 'metadata'
    video.muted = true
    video.playsInline = true

    // 监听元数据加载完成
    video.onloadedmetadata = () => {
      console.log('[视频帧提取] 元数据加载完成:', {
        videoWidth: video.videoWidth,
        videoHeight: video.videoHeight,
        duration: `${video.duration.toFixed(2)}s`
      })
      
      // 设置 canvas 尺寸为视频尺寸
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      // 设置视频时间点
      const seekTime = Math.min(timeOffset, video.duration)
      console.log('[视频帧提取] 准备跳转到时间点:', seekTime)
      video.currentTime = seekTime
    }

    // 监听 seeked 事件（当 currentTime 设置完成后触发）
    video.onseeked = () => {
      console.log('[视频帧提取] 已跳转到目标时间点，开始绘制帧')
      
      try {
        // 绘制当前帧到 canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        console.log('[视频帧提取] 帧已绘制到 canvas')

        // 转换为 Blob
        canvas.toBlob(
          (blob) => {
            // 清理资源
            URL.revokeObjectURL(video.src)
            video.remove()
            canvas.remove()

            if (blob) {
              console.log('[视频帧提取] ✅ 成功生成 Blob:', {
                size: `${(blob.size / 1024).toFixed(2)}KB`,
                type: blob.type
              })
              resolve(blob)
            } else {
              console.error('[视频帧提取] ❌ 无法生成图片 Blob')
              reject(new Error('无法生成图片 Blob'))
            }
          },
          'image/jpeg',
          0.95
        )
      } catch (error) {
        console.error('[视频帧提取] ❌ 绘制或转换失败:', error)
        // 清理资源
        URL.revokeObjectURL(video.src)
        video.remove()
        canvas.remove()
        reject(error)
      }
    }

    video.onerror = (e) => {
      console.error('[视频帧提取] ❌ 视频加载失败:', e)
      URL.revokeObjectURL(video.src)
      video.remove()
      canvas.remove()
      reject(new Error('视频加载失败'))
    }

    // 创建对象 URL 并加载视频
    const videoUrl = URL.createObjectURL(file)
    console.log('[视频帧提取] 创建视频对象 URL，开始加载')
    video.src = videoUrl
    video.load()
  })
}

/**
 * 从视频 Blob 提取第一帧并转换为 File 对象
 * @param videoFile 视频文件
 * @param timeOffset 提取帧的时间偏移（秒）
 * @returns 第一帧的 File 对象（用于取色分析）
 */
export async function extractFirstFrameAsFile(
  videoFile: File,
  timeOffset: number = 0.1
): Promise<File> {
  const frameBlob = await extractFirstFrameFromVideo(videoFile, timeOffset)
  
  // 生成文件名
  const fileName = `${videoFile.name.replace(/\.[^.]+$/, '')}_frame.jpg`
  
  // 将 Blob 转换为 File
  return new File([frameBlob], fileName, { type: 'image/jpeg' })
}

/**
 * 检测文件是否为视频
 * @param file 文件对象
 * @returns 是否为视频文件
 */
export function isVideoFile(file: File): boolean {
  return file.type.startsWith('video/')
}

/**
 * 检测文件是否为图片
 * @param file 文件对象
 * @returns 是否为图片文件
 */
export function isImageFile(file: File): boolean {
  return file.type.startsWith('image/')
}
