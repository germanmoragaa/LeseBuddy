import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  addItemsToDeck,
  createDeck,
  deleteDeck,
  listDecks,
  removeItemFromDeck,
  updateDeck,
} from '../../lib/api'
import type { DeckCreatePayload, DeckUpdatePayload } from '../../types/deck'

export function useDecks() {
  return useQuery({ queryKey: ['decks'], queryFn: listDecks })
}

export function useCreateDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: DeckCreatePayload) => createDeck(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
    },
  })
}

export function useRenameDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ deckId, payload }: { deckId: string; payload: DeckUpdatePayload }) =>
      updateDeck(deckId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
    },
  })
}

export function useDeleteDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (deckId: string) => deleteDeck(deckId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })
}

export function useAddItemsToDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      deckId,
      vocabularyItemIds,
    }: {
      deckId: string
      vocabularyItemIds: string[]
    }) => addItemsToDeck(deckId, vocabularyItemIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary-item'] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })
}

export function useRemoveItemFromDeck() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ deckId, vocabularyItemId }: { deckId: string; vocabularyItemId: string }) =>
      removeItemFromDeck(deckId, vocabularyItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['decks'] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary'] })
      queryClient.invalidateQueries({ queryKey: ['vocabulary-item'] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })
}
