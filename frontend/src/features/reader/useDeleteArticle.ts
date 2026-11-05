import { useMutation, useQueryClient } from '@tanstack/react-query'

import { deleteArticle } from '../../lib/api'

export function useDeleteArticle(articleId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => deleteArticle(articleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] })
      queryClient.removeQueries({ queryKey: ['article', articleId] })
    },
  })
}
