"use client"

import Image from "next/image"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

// A simple logo component for the Iris sidebar.  This replaces the old
// Kortix logo with the Iris symbol.  The image automatically inverts
// when the site is in dark mode.
export function IrisLogo() {
  const { theme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // Wait until after mount before accessing the theme; otherwise the
  // `theme` value may be undefined during server-side rendering.
  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="flex h-6 w-6 items-center justify-center flex-shrink-0">
      {/* Use the Iris symbol instead of the Kortix symbol.  The image
          contains the stylized eye logo used across the Iris brand. */}
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