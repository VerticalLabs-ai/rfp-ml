import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileText, AlertCircle, Settings as SettingsIcon } from 'lucide-react'
import { toast } from 'sonner'

import ProposalEditor from '@/components/ProposalEditor'

const Card = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
  <div className={`bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm ${className}`}>
    {children}
  </div>
)

export default function SettingsPage() {
  const [uploading, setUploading] = useState(false)

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      // Direct fetch since api helper might not support form data yet or needs update
      const res = await fetch('/api/v1/generation/style/upload', {
        method: 'POST',
        body: formData
      })
      if (!res.ok) throw new Error('Upload failed')
      return res.json()
    },
    onSuccess: () => {
      toast.success("Style reference uploaded successfully")
      setUploading(false)
    },
    onError: () => {
      toast.error("Failed to upload style reference")
      setUploading(false)
    }
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploading(true)
      uploadMutation.mutate(e.target.files[0])
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <SettingsIcon className="h-6 w-6 text-blue-500" />
            Settings & Configuration
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Manage system preferences and AI tuning.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Brand Voice / Style Tuning */}
        <Card className="p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold text-lg">Brand Voice & Style Tuning</h3>
              <p className="text-sm text-slate-500 mt-1">
                Upload past winning proposals to train the AI on your writing style.
              </p>
            </div>
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>

          <div className="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors relative">
            <input 
              type="file" 
              accept=".txt,.md" 
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <div className="flex flex-col items-center gap-3">
              <div className="h-12 w-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                {uploading ? (
                   <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full"/>
                ) : (
                   <Upload className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                )}
              </div>
              <div className="space-y-1">
                <p className="font-medium text-slate-900 dark:text-white">
                  {uploading ? "Uploading..." : "Click to upload or drag and drop"}
                </p>
                <p className="text-xs text-slate-500">
                  Supported formats: .txt, .md (PDF coming soon)
                </p>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg flex gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
            <div className="text-xs text-yellow-800 dark:text-yellow-200">
              <p className="font-semibold">Privacy Note</p>
              <p>Uploaded documents are processed locally for style embedding and are not shared externally.</p>
            </div>
          </div>
        </Card>

        {/* Editor Preview */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Editor Co-Pilot Preview</h3>
          <ProposalEditor 
            initialContent="<h3>Executive Summary</h3><p>Highlight this text to test the AI refinement capabilities. The magic overlay will appear and allow you to rewrite sections instantly.</p>"
          />
        </div>
      </div>
    </div>
  )
}
