import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Briefcase, ExternalLink } from "lucide-react"
// Removed KortixProcessModal import because the CTA no longer includes the enterprise modal.

export function CTACard() {
  return (
    <div className="flex flex-col space-y-2 py-2 px-1">
      {/* Update CTA to encourage users to provide feedback instead of
          advertising career opportunities.  Users can earn free
          Vision Gems by helping improve Iris. */}
      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground">Feedback Rewards</span>
        <span className="text-xs text-muted-foreground mt-0.5">Give feedback and earn free vision gems</span>
      </div>
      <div className="flex flex-col space-y-2">
        {/* You can link this button to a feedback form or other page where users
            can share their experience.  For now, it links to the Iris feedback page. */}
        <Link href="https://irisai.vision/feedback" target="_blank" rel="noopener noreferrer">
          <Button 
            variant="outline" 
            size="sm" 
            className="w-full text-xs"
          >
            Give Feedback
            <ExternalLink className="ml-1.5 h-3 w-3" />
          </Button>
        </Link>
      </div>
    </div>
  )
}
