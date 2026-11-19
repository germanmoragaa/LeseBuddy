import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ExternalLink, Lock, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router'

import { Button } from '../../components/Button'
import { ApiError, isApiErrorDetail, saveSong } from '../../lib/api'
import type { SongSearchResult } from '../../types/song'
import { SongCover } from './SongCover'
import { releaseLabel } from './songFormat'

const LYRICS_MAX_LENGTH = 50_000

interface AddSongDialogProps {
  song: SongSearchResult
  onClose: () => void
}

function existingArticleId(error: unknown): string | null {
  if (
    error instanceof ApiError &&
    error.status === 409 &&
    isApiErrorDetail(error.detail) &&
    error.detail.code === 'song_already_saved'
  ) {
    const articleId = (error.detail as { article_id?: unknown }).article_id
    return typeof articleId === 'string' ? articleId : null
  }
  return null
}

function saveErrorMessage(error: unknown): string {
  if (error instanceof ApiError && isApiErrorDetail(error.detail)) {
    if (error.detail.code === 'song_not_found') return "Genius doesn't have this song anymore."
    if (error.detail.code === 'songs_not_configured') return "Song search isn't set up yet."
  }
  return "Couldn't save the song. Please try again."
}

// Rendered into document.body: the app header uses backdrop-blur, which would otherwise make
// this fixed overlay position itself inside the header instead of the viewport.
export function AddSongDialog({ song, onClose }: AddSongDialogProps) {
  const headingId = useId()
  const lyricsId = useId()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [lyrics, setLyrics] = useState('')
  const isTooLong = lyrics.length > LYRICS_MAX_LENGTH
  const release = releaseLabel(song)

  const mutation = useMutation({
    mutationFn: saveSong,
    onSuccess: (article) => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      onClose()
      navigate(`/app/reader/${article.id}`)
    },
  })
  const duplicateId = existingArticleId(mutation.error)

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <button
        type="button"
        aria-label="Close add song"
        tabIndex={-1}
        onClick={onClose}
        className="absolute inset-0 w-full border-0 bg-black/30"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        className="relative flex max-h-[90dvh] w-full max-w-[520px] flex-col overflow-y-auto rounded-lg border border-line bg-white p-6 shadow-card"
      >
        <div className="flex items-start gap-3.5">
          <SongCover url={song.cover_url ?? song.thumbnail_url} size="lg" />
          <div className="min-w-0 flex-1">
            <span className="text-[10px] font-extrabold uppercase tracking-wide text-action">
              Add song
            </span>
            <h2 id={headingId} className="truncate text-[20px] tracking-tight">
              {song.title}
            </h2>
            <p className="truncate text-[11px] text-muted">
              {song.primary_artist}
              {release ? ` · ${release}` : ''}
            </p>
            {song.genius_url && (
              <a
                href={song.genius_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-flex items-center gap-1 text-[10px] font-bold text-action hover:underline"
              >
                View on Genius <ExternalLink size={11} aria-hidden="true" />
              </a>
            )}
          </div>
          <Button variant="icon" aria-label="Close" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </Button>
        </div>

        <label htmlFor={lyricsId} className="mt-5 mb-1.5 block text-[11px] font-bold">
          Lyrics
        </label>
        <textarea
          id={lyricsId}
          ref={textareaRef}
          value={lyrics}
          onChange={(event) => setLyrics(event.target.value)}
          placeholder="Paste the song's lyrics here…"
          className="min-h-[200px] w-full resize-y rounded-sm border border-line px-3.5 pt-3.5 text-[11px] text-ink outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
        />
        <small className="mt-1 block text-right text-[9px] text-muted">
          {lyrics.split(/\s+/).filter(Boolean).length} words
        </small>

        <p className="mt-2 flex gap-2 rounded-sm bg-accent-soft p-3 text-[10px] text-ink">
          <Lock size={14} aria-hidden="true" className="mt-px shrink-0" />
          <span>
            Lyrics stay private in your library and are only for your personal study. Only add
            lyrics you have the right to use.
          </span>
        </p>

        {isTooLong && (
          <p role="alert" className="mt-3 text-[10px] text-danger">
            The lyrics are too long ({lyrics.length.toLocaleString()} characters). Please keep
            them under {LYRICS_MAX_LENGTH.toLocaleString()} characters.
          </p>
        )}
        {mutation.isError &&
          (duplicateId ? (
            <div
              role="alert"
              className="mt-3 flex items-center justify-between gap-3 rounded-sm bg-surface-mint px-3.5 py-2.5 text-[11px] text-ink"
            >
              <span>This song is already in your library.</span>
              <Button
                variant="secondary"
                onClick={() => {
                  onClose()
                  navigate(`/app/reader/${duplicateId}`)
                }}
              >
                Open it
              </Button>
            </div>
          ) : (
            <p
              role="alert"
              className="mt-3 rounded-sm bg-surface-coral px-3.5 py-2.5 text-[11px] text-danger"
            >
              {saveErrorMessage(mutation.error)}
            </p>
          ))}

        <Button
          className="mt-4 w-full"
          disabled={lyrics.trim().length === 0 || isTooLong || mutation.isPending}
          onClick={() => mutation.mutate({ genius_song_id: song.genius_id, lyrics_text: lyrics })}
        >
          {mutation.isPending ? 'Adding…' : 'Add song and start reading'}{' '}
          <ArrowRight size={18} aria-hidden="true" />
        </Button>
      </div>
    </div>,
    document.body,
  )
}
