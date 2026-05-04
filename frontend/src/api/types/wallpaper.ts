export interface WallpaperStatus {
  has_wallpaper: boolean
  wallpaper_type: 'image' | 'video' | 'none'
  wallpaper_blur: number
  wallpaper_opacity: number
}
