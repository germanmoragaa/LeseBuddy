import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, ChevronLeft, ChevronRight, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { Card } from '../../components/Card'
import { listArticles, updateArticle } from '../../lib/api'
import type { ArticleListItem } from '../../types/article'
import { useDeleteArticle } from './useDeleteArticle'

const PAGE_SIZE = 20
const WORDS_PER_MINUTE = 200

function estimatedReadMinutes(wordCount: number) {
  return Math.max(1, Math.ceil(wordCount / WORDS_PER_MINUTE))
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function ArticleRow({
  article,
  onOpen,
}: {
  article: ArticleListItem
  onOpen: (id: string) => void
}) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState(article.title ?? '')

  const renameMutation = useMutation({
    mutationFn: () => updateArticle(article.id, { title: title.trim() }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useDeleteArticle(article.id)

  function startEditing() {
    setTitle(article.title ?? '')
    setIsEditing(true)
  }

  function handleDelete() {
    if (window.confirm('Delete this text from your library? This cannot be undone.')) {
      deleteMutation.mutate()
    }
  }

  return (
    <div className="border-b border-line px-5 py-4 last:border-b-0">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid h-9 w-8 shrink-0 place-items-center rounded-[5px_8px_8px_5px] bg-[#f2e6d0] text-brand">
          <BookOpen size={18} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                aria-label="Article title"
                autoFocus
                className="min-w-0 flex-1 rounded-sm border border-line px-2.5 py-1.5 text-[12px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
              />
              <Button
                variant="secondary"
                className="min-h-[34px] px-3 text-[11px]"
                onClick={() => renameMutation.mutate()}
                disabled={title.trim().length === 0 || renameMutation.isPending}
              >
                {renameMutation.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button
                variant="ghost"
                className="min-h-[34px] px-3 text-[11px]"
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => onOpen(article.id)}
              className="block w-full text-left"
            >
              <strong className="block truncate text-[13px]">
                {article.title ?? 'Untitled text'}
              </strong>
              {article.excerpt && (
                <p className="mt-1 line-clamp-2 text-[11px] text-muted">{article.excerpt}</p>
              )}
            </button>
          )}
          {renameMutation.isError && (
            <p className="mt-1 text-[10px] text-danger" role="alert">
              Couldn't rename this text.
            </p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[9px] text-muted">
            <span>{article.word_count} words</span>
            <span aria-hidden="true">·</span>
            <span>{estimatedReadMinutes(article.word_count)} min read</span>
            <span aria-hidden="true">·</span>
            <span>{formatDate(article.created_at)}</span>
          </div>
        </div>
        {!isEditing && (
          <div className="flex shrink-0 gap-1.5">
            <Button
              variant="icon"
              aria-label="Rename text"
              onClick={startEditing}
              className="min-h-[34px] w-[34px]"
            >
              <Pencil size={15} aria-hidden="true" />
            </Button>
            <Button
              variant="icon"
              aria-label="Delete text"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="min-h-[34px] w-[34px]"
            >
              <Trash2 size={15} aria-hidden="true" />
            </Button>
          </div>
        )}
      </div>
      {deleteMutation.isError && (
        <p className="mt-2 text-[10px] text-danger" role="alert">
          Couldn't delete this text.
        </p>
      )}
    </div>
  )
}

export function ReaderLibrary() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const listQuery = useQuery({
    queryKey: ['articles', page],
    queryFn: () => listArticles({ page, pageSize: PAGE_SIZE }),
  })

  const items = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div className="mb-7 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <span className="block text-[11px] font-bold uppercase tracking-wide text-muted">
            Your library
          </span>
          <h1 className="my-1.5 text-[33px] tracking-tight">Reader</h1>
          <p className="m-0 text-[13px] text-muted">
            Every text you've added, newest first.
          </p>
        </div>
        <Button onClick={() => navigate('/app/reader/new')}>
          <Plus size={18} aria-hidden="true" /> Add a text
        </Button>
      </div>

      <Card className="overflow-hidden">
        {listQuery.isPending && <p className="px-5 py-10 text-center text-sm text-muted">Loading…</p>}
        {listQuery.isError && (
          <div className="flex flex-col items-center gap-3 px-5 py-10 text-center">
            <p className="text-sm text-danger" role="alert">
              Couldn't load your reading library.
            </p>
            <Button variant="secondary" onClick={() => listQuery.refetch()}>
              Try again
            </Button>
          </div>
        )}

        {listQuery.data && items.length === 0 && (
          <div className="flex flex-col items-center gap-3 px-5 py-14 text-center">
            <p className="text-sm text-muted">
              You haven't added any texts yet. Paste a German text to get started.
            </p>
            <Button onClick={() => navigate('/app/reader/new')}>
              <Plus size={18} aria-hidden="true" /> Add a text
            </Button>
          </div>
        )}

        {items.map((article) => (
          <ArticleRow
            key={article.id}
            article={article}
            onOpen={(id) => navigate(`/app/reader/${id}`)}
          />
        ))}
      </Card>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button
            variant="icon"
            aria-label="Previous page"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            <ChevronLeft size={18} aria-hidden="true" />
          </Button>
          <span className="text-[11px] text-muted">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="icon"
            aria-label="Next page"
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page >= totalPages}
          >
            <ChevronRight size={18} aria-hidden="true" />
          </Button>
        </div>
      )}
    </div>
  )
}
