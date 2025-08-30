"use client"

import Image from "next/image"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

export function KortixLogo() {
  const { theme } = useTheme()
  const [mounted, setMounted] = useState(false)
  
  // After mount, we can access the theme
  useEffect(() => {
    setMounted(true)
  }, [])
  
  return (
    <div className="flex h-6 w-6 items-center justify-center flex-shrink-0">
      {/* Use the Iris symbol instead of the Kortix symbol.  The image contains
          the stylized eye logo used across the Iris brand. */}
      <Image
        src="/iris-symbol.png"
        alt="Iris"
        width={24}
        height={24}
        className={`${mounted && theme === 'dark' ? 'invert' : ''}`}
      />
    </div>
  )
} 