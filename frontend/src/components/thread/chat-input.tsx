'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send, Square, Loader2, X, Paperclip, ChevronDown, Check } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";

// Define API_URL
const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

// Local storage keys (unused currently, reserved for future Iris-specific settings)
const STORAGE_KEY_MODEL = 'iris-preferred-model';

interface ChatInputProps {
  onSubmit: (message: string) => void;
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
  isAgentRunning?: boolean;
  onStopAgent?: () => void;
  autoFocus?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  onFileBrowse?: () => void;
  sandboxId?: string;
  hideAttachments?: boolean;
}

interface UploadedFile {
  name: string;
  path: string; // workspace-relative (no leading slash)
  size: number;
  mime?: string;
  previewable?: boolean;
  downloadUrl?: string;
  status: 'uploading' | 'done' | 'error';
  progress: number; // 0-100
}

export function ChatInput({
  onSubmit,
  placeholder = "Describe what you need help with...",
  loading = false,
  disabled = false,
  isAgentRunning = false,
  onStopAgent,
  autoFocus = true,
  value: controlledValue,
  onChange: controlledOnChange,
  onFileBrowse,
  sandboxId,
  hideAttachments = false
}: ChatInputProps) {
  const isControlled = controlledValue !== undefined && controlledOnChange !== undefined;
  
  const [uncontrolledValue, setUncontrolledValue] = useState('');
  const value = isControlled ? controlledValue : uncontrolledValue;

  // A single model is used for all requests.  Multi‑model support has been
  // removed, so we no longer track a selected model in local state.
  const selectedModel = "iris";
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  
  // When multi‑model support existed we persisted the selected model to
  // localStorage.  With a single model there is no preference to load, so
  // this effect is intentionally left blank.
  useEffect(() => {
    /* no-op */
  }, []);
  
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const adjustHeight = () => {
      textarea.style.height = 'auto';
      const newHeight = Math.min(Math.max(textarea.scrollHeight, 24), 200);
      textarea.style.height = `${newHeight}px`;
    };

    adjustHeight();
    
    adjustHeight();

    window.addEventListener('resize', adjustHeight);
    return () => window.removeEventListener('resize', adjustHeight);
  }, [value]);

  // Single-model system; no model change handler required.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!value.trim() && uploadedFiles.length === 0) || loading || (disabled && !isAgentRunning)) return;
    
    if (isAgentRunning && onStopAgent) {
      onStopAgent();
      return;
    }
    
    let message = value;
    
    if (uploadedFiles.length > 0) {
      const fileInfo = uploadedFiles.map(file => 
        `[Uploaded File: ${file.path}]`
      ).join('\n');
      message = message ? `${message}\n\n${fileInfo}` : fileInfo;
    }
    
    // Single-model: submit without model options; backend uses Gemini 2.5 Pro.
    onSubmit(message);
    
    if (!isControlled) {
      setUncontrolledValue("");
    }
    
    setUploadedFiles([]);
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    if (isControlled) {
      controlledOnChange(newValue);
    } else {
      setUncontrolledValue(newValue);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if ((value.trim() || uploadedFiles.length > 0) && !loading && (!disabled || isAgentRunning)) {
        handleSubmit(e as React.FormEvent);
      }
    }
  };

  const handleFileUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    
    if (!sandboxId || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return;
    
    const files = Array.from(e.dataTransfer.files);
    await uploadFiles(files);
  };

  const processFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!sandboxId || !event.target.files || event.target.files.length === 0) return;
    
    const files = Array.from(event.target.files);
    await uploadFiles(files);
    
    event.target.value = '';
  };

  const uploadFiles = async (files: File[]) => {
    if (!sandboxId) return;
    try {
      setIsUploading(true);
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error('No access token available');

      for (const file of files) {
        if (file.size > 50 * 1024 * 1024) {
          toast.error(`File size exceeds 50MB limit: ${file.name}`);
          continue;
        }

        // Normalize and enrich attachment metadata
        const baseName = file.name.replace(/^\/+/, '');
        const uploadPath = `workspace/${baseName}`; // workspace-relative, no leading slash
        const ext = baseName.split('.').pop()?.toLowerCase() || '';
        const previewable = [
          'txt','md','json','csv','xml','html','css','js','ts','py','tsx','jsx'
        ].includes(ext);
        const downloadUrl = `${API_URL}/api/sandboxes/${sandboxId}/files/content?path=${encodeURIComponent(uploadPath)}`;

        // Seed UI chip in uploading state
        setUploadedFiles(prev => [
          ...prev,
          {
            name: baseName,
            path: uploadPath,
            size: file.size,
            mime: file.type || undefined,
            previewable,
            downloadUrl,
            status: 'uploading',
            progress: 0
          }
        ]);

        await new Promise<void>((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          xhr.open('POST', `${API_URL}/api/sandboxes/${sandboxId}/files`);
          xhr.setRequestHeader('Authorization', `Bearer ${session.access_token}`);

          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              const pct = Math.round((e.loaded / e.total) * 100);
              setUploadedFiles(prev => prev.map(f => f.path === uploadPath ? { ...f, progress: pct } : f));
            }
          };

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              setUploadedFiles(prev => prev.map(f => f.path === uploadPath ? { ...f, status: 'done', progress: 100 } : f));
              toast.success(`Uploaded: ${file.name}`);
              resolve();
            } else {
              setUploadedFiles(prev => prev.map(f => f.path === uploadPath ? { ...f, status: 'error' } : f));
              reject(new Error(`Upload failed: ${xhr.statusText || xhr.status}`));
            }
          };

          xhr.onerror = () => {
            setUploadedFiles(prev => prev.map(f => f.path === uploadPath ? { ...f, status: 'error' } : f));
            reject(new Error('Network error during upload'));
          };

          const formData = new FormData();
          formData.append('file', file);
          formData.append('path', uploadPath);
          xhr.send(formData);
        });
      }
    } catch (error) {
      console.error("File upload failed:", error);
      toast.error(error instanceof Error ? error.message : "Failed to upload file");
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    // Intentionally not shown in the chip to reduce clutter; keep util for future
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const removeUploadedFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Multi‑model options have been removed.  If you reintroduce support for
  // additional models in the future, define them here.
  const modelOptions: never[] = [];

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-4">
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-2 overflow-hidden"
          >
            <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
              {uploadedFiles.map((file, index) => (
                <motion.div 
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.15 }}
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded-md flex items-center gap-1.5 group text-sm"
                >
                  {file.status === 'uploading' ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
                  ) : file.status === 'done' ? (
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <X className="h-3.5 w-3.5 text-red-600" />
                  )}
                  <span className="truncate max-w-[140px] text-gray-700 dark:text-gray-300">{file.name}</span>
                  {file.status === 'uploading' && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">{file.progress}%</span>
                  )}
                  <Button 
                    type="button" 
                    variant="ghost" 
                    size="icon" 
                    className="h-4 w-4 rounded-full p-0 hover:bg-gray-200 dark:hover:bg-gray-700"
                    onClick={() => removeUploadedFile(index)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div 
        className={cn(
          "flex items-end w-full rounded-lg border border-gray-200 dark:border-gray-900 bg-white dark:bg-black px-3 py-2 shadow-sm transition-all duration-200",
          isDraggingOver ? "border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/10" : ""
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="relative flex-1 flex items-center overflow-hidden dark:bg-black">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={cn(
              "min-h-[24px] max-h-[200px] py-0 px-0 text-sm resize-none border-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 bg-transparent w-full dark:bg-black",
              isDraggingOver ? "opacity-40" : ""
            )}
            disabled={loading || (disabled && !isAgentRunning)}
            rows={1}
          />
        </div>
        
        <div className="flex items-center gap-2 pl-2 flex-shrink-0">
          {/* Single-model: model settings are removed */}
          
          {!hideAttachments && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    type="button"
                    onClick={handleFileUpload}
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                    disabled={loading || (disabled && !isAgentRunning) || isUploading}
                  >
                    {isUploading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Paperclip className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">
                  <p>Attach files</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={processFileUpload}
            multiple
          />
          
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  type="submit"
                  onClick={isAgentRunning ? onStopAgent : handleSubmit}
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-8 w-8 rounded-md",
                    isAgentRunning 
                      ? "text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30" 
                      : "text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800",
                    ((!value.trim() && uploadedFiles.length === 0) && !isAgentRunning) || loading || (disabled && !isAgentRunning) 
                      ? "opacity-50" 
                      : ""
                  )}
                  disabled={((!value.trim() && uploadedFiles.length === 0) && !isAgentRunning) || loading || (disabled && !isAgentRunning)}
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : isAgentRunning ? (
                    <Square className="h-4 w-4" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>{isAgentRunning ? 'Stop agent' : 'Send message'}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {isAgentRunning && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 w-full flex items-center justify-center"
        >
          <div className="text-xs text-muted-foreground flex items-center gap-2">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Starting computer…</span>
          </div>
        </motion.div>
      )}
    </div>
  );
} 
