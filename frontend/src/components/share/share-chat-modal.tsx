import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  Share2, 
  Copy, 
  ExternalLink, 
  Eye, 
  EyeOff, 
  Clock, 
  Users, 
  Globe,
  Lock,
  CheckCircle,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { createShare, getThreadShare, deleteShare, ShareRequest } from '@/lib/api';

interface ShareChatModalProps {
  threadId: string;
  projectName?: string;
  messageCount?: number;
  onShare?: (shareData: ShareData) => void;
  trigger?: React.ReactNode;
}

interface ShareData {
  threadId: string;
  isPublic: boolean;
  title?: string;
  description?: string;
  allowComments?: boolean;
  expiresAt?: string;
  shareUrl: string;
}

export const ShareChatModal: React.FC<ShareChatModalProps> = ({
  threadId,
  projectName = "Untitled Project",
  messageCount = 0,
  onShare,
  trigger
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shareData, setShareData] = useState<ShareData | null>(null);
  
  // Form state
  const [title, setTitle] = useState(projectName);
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [allowComments, setAllowComments] = useState(false);
  const [expiresIn, setExpiresIn] = useState<'never' | '7d' | '30d' | '90d'>('never');
  
  const generateShareUrl = (threadId: string) => {
    const baseUrl = process.env.NEXT_PUBLIC_URL || window.location.origin;
    return `${baseUrl}/share/${threadId}`;
  };
  
  const handleShare = async () => {
    setIsLoading(true);
    
    try {
      // Calculate expiration date
      let expiresAt: string | undefined;
      if (expiresIn !== 'never') {
        const days = parseInt(expiresIn.replace('d', ''));
        const expireDate = new Date();
        expireDate.setDate(expireDate.getDate() + days);
        expiresAt = expireDate.toISOString();
      }
      
      // Create share request
      const shareRequest: ShareRequest = {
        title: title || projectName,
        description,
        is_public: isPublic,
        allow_comments: allowComments,
        expires_at: expiresAt
      };
      
      // Make API call to create share
      const shareResponse = await createShare(threadId, shareRequest);
      
      // Create share data for UI
      const newShareData: ShareData = {
        threadId,
        isPublic,
        title: shareResponse.title || title || projectName,
        description: shareResponse.description || description,
        allowComments: shareResponse.allow_comments,
        expiresAt: shareResponse.expires_at,
        shareUrl: shareResponse.url
      };
      
      setShareData(newShareData);
      
      if (onShare) {
        onShare(newShareData);
      }
      
      toast.success('Chat shared successfully!');
      
    } catch (error) {
      console.error('Error sharing chat:', error);
      toast.error(`Failed to share chat: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };
  
  const copyShareUrl = () => {
    if (shareData?.shareUrl) {
      navigator.clipboard.writeText(shareData.shareUrl);
      toast.success('Share URL copied to clipboard!');
    }
  };
  
  const openInNewTab = () => {
    if (shareData?.shareUrl) {
      window.open(shareData.shareUrl, '_blank');
    }
  };
  
  const resetForm = () => {
    setTitle(projectName);
    setDescription('');
    setIsPublic(true);
    setAllowComments(false);
    setExpiresIn('never');
    setShareData(null);
  };
  
  useEffect(() => {
    if (!isOpen) {
      // Reset form when modal closes
      setTimeout(resetForm, 300);
    }
  }, [isOpen, projectName]);
  
  const defaultTrigger = (
    <Button variant="outline" size="sm" className="gap-2">
      <Share2 className="h-4 w-4" />
      Share Chat
    </Button>
  );
  
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            Share Chat Replay
          </DialogTitle>
        </DialogHeader>
        
        {!shareData ? (
          // Share configuration form
          <div className="space-y-6">
            {/* Chat info */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">Chat Details</h4>
                <Badge variant="outline" className="text-xs">
                  {messageCount} messages
                </Badge>
              </div>
              <p className="text-sm text-gray-600 truncate">{projectName}</p>
            </div>
            
            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Share Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a title for your shared chat"
                className="w-full"
              />
            </div>
            
            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a description to help others understand the context"
                rows={3}
                className="w-full resize-none"
              />
            </div>
            
            {/* Visibility */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isPublic ? (
                    <Globe className="h-4 w-4 text-green-600" />
                  ) : (
                    <Lock className="h-4 w-4 text-gray-600" />
                  )}
                  <Label htmlFor="public">Public Access</Label>
                </div>
                <Switch
                  id="public"
                  checked={isPublic}
                  onCheckedChange={setIsPublic}
                />
              </div>
              <p className="text-xs text-gray-500">
                {isPublic 
                  ? "Anyone with the link can view this chat replay"
                  : "Only people you explicitly share with can access this chat"
                }
              </p>
            </div>
            
            {/* Comments */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-gray-600" />
                  <Label htmlFor="comments">Allow Comments</Label>
                </div>
                <Switch
                  id="comments"
                  checked={allowComments}
                  onCheckedChange={setAllowComments}
                />
              </div>
              <p className="text-xs text-gray-500">
                Let viewers leave comments on your shared chat
              </p>
            </div>
            
            {/* Expiration */}
            <div className="space-y-2">
              <Label>Link Expiration</Label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'never', label: 'Never' },
                  { value: '7d', label: '7 days' },
                  { value: '30d', label: '30 days' },
                  { value: '90d', label: '90 days' }
                ].map((option) => (
                  <Button
                    key={option.value}
                    variant={expiresIn === option.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setExpiresIn(option.value as any)}
                    className="justify-center"
                  >
                    <Clock className="h-3 w-3 mr-1" />
                    {option.label}
                  </Button>
                ))}
              </div>
            </div>
            
            {/* Share button */}
            <Button 
              onClick={handleShare} 
              disabled={isLoading || !title.trim()}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Creating Share Link...
                </>
              ) : (
                <>
                  <Share2 className="h-4 w-4 mr-2" />
                  Create Share Link
                </>
              )}
            </Button>
          </div>
        ) : (
          // Share success view
          <div className="space-y-6">
            {/* Success message */}
            <div className="text-center py-4">
              <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Chat Shared Successfully!
              </h3>
              <p className="text-sm text-gray-600">
                Your chat replay is now available at the link below
              </p>
            </div>
            
            {/* Share URL */}
            <div className="space-y-3">
              <Label>Share URL</Label>
              <div className="flex gap-2">
                <Input
                  value={shareData.shareUrl}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyShareUrl}
                  className="shrink-0"
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openInNewTab}
                  className="shrink-0"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            {/* Share details */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Visibility</span>
                <div className="flex items-center gap-1">
                  {shareData.isPublic ? (
                    <>
                      <Globe className="h-3 w-3 text-green-600" />
                      <span className="text-xs text-green-700">Public</span>
                    </>
                  ) : (
                    <>
                      <Lock className="h-3 w-3 text-gray-600" />
                      <span className="text-xs text-gray-700">Private</span>
                    </>
                  )}
                </div>
              </div>
              
              {shareData.expiresAt && (
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Expires</span>
                  <span className="text-xs text-gray-600">
                    {new Date(shareData.expiresAt).toLocaleDateString()}
                  </span>
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Comments</span>
                <span className="text-xs text-gray-600">
                  {shareData.allowComments ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShareData(null)}
                className="flex-1"
              >
                Create New Link
              </Button>
              <Button
                onClick={() => setIsOpen(false)}
                className="flex-1"
              >
                Done
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

