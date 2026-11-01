export interface ArticleMeta {
  id: string
  title: string
  deck: string
  category: string
  dateLabel: string
  levelLabel: string
  wordCount: number
  readMinutes: number
}

export interface ArticleParagraphPart {
  text: string
  wordKey?: string
}

export type ArticleParagraph = ArticleParagraphPart[]

export interface WordExplanation {
  partOfSpeech: string
  meaning: string
  note?: string
  contextSentence: string
  contextTranslation: string
  example?: string
  exampleTranslation?: string
}
