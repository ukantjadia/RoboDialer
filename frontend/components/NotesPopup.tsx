import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { FiBold, FiItalic, FiList, FiLink, FiEye, FiCode } from 'react-icons/fi';
import Notif from './ui/notif';

interface NotesPopupProps {
  leadId: string;
  type: 'company' | 'person';
  name: string;
  open: boolean;
  onClose: () => void;
  baseUrl: string;
  onNoteStatusChange?: (hasNote: boolean) => void;
}

export function NotesPopup({ leadId, type, name, open, onClose, baseUrl, onNoteStatusChange }: NotesPopupProps) {
  const [note, setNote] = useState('');
  const [isPreview, setIsPreview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notif, setNotif] = useState({
    show: false,
    message: '',
    type: 'success' as 'success' | 'error' | 'info'
  });

  const noteUrl = type === 'person'
    ? `${baseUrl}/drafts/${leadId}/person/note`
    : `${baseUrl}/drafts/${leadId}/note`;

  // Load note when popup opens
  useEffect(() => {
    if (!open) return;
    
    setLoading(true);
    setNotif({ show: false, message: '', type: 'success' });
    
    axios.get(noteUrl, { withCredentials: true })
      .then((res) => {
        setNote(res.data.content || '');
        onNoteStatusChange?.(!!res.data.content);
      })
      .catch((err) => {
        setNotif({
          show: true,
          message: err.response?.data?.error || 'Failed to load note',
          type: 'error'
        });
        onNoteStatusChange?.(false);
      })
      .finally(() => setLoading(false));
  }, [open, noteUrl]);

  const handleSave = async () => {
    setSaving(true);
    setNotif({ show: false, message: '', type: 'success' });
    
    try {
      await axios.post(noteUrl, { note }, { withCredentials: true });
      setNotif({ show: true, message: 'Note saved!', type: 'success' });
      onNoteStatusChange?.(!!note);
      onClose();
    } catch (err: any) {
      setNotif({
        show: true,
        message: err.response?.data?.error || 'Failed to save note',
        type: 'error'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setSaving(true);
    setNotif({ show: false, message: '', type: 'success' });
    
    try {
      await axios.delete(noteUrl, { withCredentials: true });
      setNote('');
      setNotif({ show: true, message: 'Note deleted!', type: 'success' });
      onNoteStatusChange?.(false);
      onClose();
    } catch (err: any) {
      setNotif({
        show: true,
        message: err.response?.data?.error || 'Failed to delete note',
        type: 'error'
      });
    } finally {
      setSaving(false);
    }
  };

  const insertMarkdown = (prefix: string, suffix: string = '') => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newValue = 
      note.substring(0, start) + 
      prefix + 
      note.substring(start, end) + 
      suffix + 
      note.substring(end);
    
    setNote(newValue);
    
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, end + prefix.length);
    }, 0);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl bg-[#181c23] text-[#f3f4f6] rounded-2xl border border-[#23272f]">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-[#facc15]">
            Notes for {name}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center items-center min-h-[350px]">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-yellow-400"></div>
          </div>
        ) : (
          <>
            {/* Toolbar */}
            <div className="flex flex-wrap gap-1 mb-2 p-1 bg-[#23272f] rounded-t-lg">
              <button onClick={() => insertMarkdown('**', '**')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiBold className="w-4 h-4" title="Bold" />
              </button>
              <button onClick={() => insertMarkdown('*', '*')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiItalic className="w-4 h-4" title="Italic" />
              </button>
              <button onClick={() => insertMarkdown('- ', '')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiList className="w-4 h-4" title="Unordered List" />
              </button>
              <button onClick={() => insertMarkdown('1. ', '')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiList className="w-4 h-4" title="Ordered List" />
              </button>
              <button onClick={() => insertMarkdown('[', '](url)')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiLink className="w-4 h-4" title="Link" />
              </button>
              <button onClick={() => insertMarkdown('```\n', '\n```')} className="p-2 hover:bg-[#2d3748] rounded">
                <FiCode className="w-4 h-4" title="Code Block" />
              </button>

              <div className="flex-1"></div>

              <button
                onClick={() => setIsPreview(!isPreview)}
                className="px-3 py-1 bg-[#374151] hover:bg-[#4b5563] rounded text-sm flex items-center gap-1"
              >
                <FiEye className="w-4 h-4" />
                {isPreview ? 'Edit' : 'Preview'}
              </button>
            </div>

            {/* Editor/Preview Area */}
            {isPreview ? (
              <div className="markdown-preview p-4 bg-[#181c23] rounded-b-lg overflow-auto min-h-[350px]">
                <ReactMarkdown
                  components={{
                    ul: (props: React.HTMLAttributes<HTMLUListElement>) => (
                      <ul className="list-disc pl-6 my-2" {...props} />
                    ),
                    ol: (props: React.OlHTMLAttributes<HTMLOListElement>) => (
                      <ol className="list-decimal pl-6 my-2" {...props} />
                    ),
                    a: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
                      <a className="text-blue-400 hover:underline" {...props} />
                    ),
                    code: (props: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) => {
                      const { inline, ...rest } = props;
                      return (
                        <code
                          className={inline
                            ? "bg-[#2d3748] px-1 py-0.5 rounded"
                            : "block bg-[#2d3748] p-2 rounded my-2 overflow-x-auto"
                          }
                          {...rest}
                        />
                      );
                    }
                  }}
                >
                  {note}
                </ReactMarkdown>
              </div>
            ) : (
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="w-full p-4 bg-[#23272f] text-[#f3f4f6] font-mono rounded-b-lg resize-none min-h-[350px]"
                placeholder="Write Markdown here..."
              />
            )}
          </>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 mt-4">
          <Button 
            variant="destructive" 
            onClick={handleDelete} 
            disabled={loading || saving || !note}
          >
            Delete
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={loading || saving || !note}
            className="bg-[#facc15] text-black hover:bg-yellow-400"
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </DialogContent>

      {/* Notification */}
      <Notif
        show={notif.show}
        message={notif.message}
        type={notif.type}
        onClose={() => setNotif(prev => ({ ...prev, show: false }))}
      />
    </Dialog>
  );
}