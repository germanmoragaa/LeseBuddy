export type VocabularyStatus = 'new' | 'learning' | 'due-soon' | 'review'

export interface VocabularyItem {
  id: string
  word: string
  meaning: string
  wordType: string
  status: VocabularyStatus
  exampleSentence: string
  sourceTitle: string
  sourceDateLabel: string
  savedDateLabel: string
  nextReviewLabel: string
  grammarNote?: string
}
