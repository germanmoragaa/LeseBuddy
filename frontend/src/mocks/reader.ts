// Placeholder data shaped like future API responses (see docs/blueprint.md section 6/8).
// The real reading workspace will fetch an article plus spaCy-derived spans and
// AI explanations per selected word — this mimics that shape with static content.

import type { ArticleMeta, ArticleParagraph, WordExplanation } from '../types/reader'

export const mockArticle: ArticleMeta = {
  id: 'warum-zu-hause-bleiben',
  title: 'Warum wir manchmal lieber zu Hause bleiben',
  deck: 'Warum ein ruhiger Abend manchmal genau das ist, was wir brauchen.',
  category: 'Mind & everyday life',
  dateLabel: '21 May 2025',
  levelLabel: 'B1–B2 · Estimated',
  wordCount: 684,
  readMinutes: 12,
}

export const mockArticleParagraphs: ArticleParagraph[] = [
  [
    {
      text: 'Nach einer langen Woche freuen sich viele Menschen darauf, endlich Zeit für sich selbst zu haben. Während einige am Wochenende gerne Freunde treffen oder neue Orte entdecken, verbringen andere lieber einen ruhigen Abend zu Hause.',
    },
  ],
  [
    { text: 'Psychologen erklären, dass dieses Bedürfnis nicht unbedingt bedeutet, dass jemand unsozial ist. Oft hilft uns eine ' },
    { text: 'vertraute', wordKey: 'vertraute' },
    { text: ' Umgebung dabei, neue Energie zu tanken. Besonders nach stressigen Tagen kann es ' },
    { text: 'wohltuend', wordKey: 'wohltuend' },
    { text: ' sein, sich bewusst Zeit für sich selbst zu nehmen.' },
  ],
  [
    { text: 'Entscheidend', wordKey: 'Entscheidend' },
    {
      text: ' ist, dass wir auf unsere eigenen Bedürfnisse hören. Wer regelmäßig Zeit allein verbringt, kann dadurch lernen, besser mit Stress umzugehen und die eigenen Gedanken zu ordnen. Gleichzeitig bleiben soziale Kontakte wichtig, denn sie geben uns Unterstützung und das Gefühl, ',
    },
    { text: 'dazuzugehören', wordKey: 'dazuzugehören' },
    { text: '.' },
  ],
]

export const mockWordExplanations: Record<string, WordExplanation> = {
  vertraute: {
    partOfSpeech: 'adjective',
    meaning: 'familiar; trusted',
    contextSentence: 'Besonders nach stressigen Tagen kann es wohltuend sein, sich bewusst Zeit für sich selbst zu nehmen.',
    contextTranslation:
      'Especially after stressful days, it can be soothing to consciously take time for yourself.',
  },
  wohltuend: {
    partOfSpeech: 'adjective',
    meaning: 'soothing; beneficial',
    note: 'Often used to describe an experience, action, or situation that has a positive, calming effect.',
    contextSentence: 'Besonders nach stressigen Tagen kann es wohltuend sein, sich bewusst Zeit für sich selbst zu nehmen.',
    contextTranslation:
      'Especially after stressful days, it can be soothing to consciously take time for yourself.',
    example: 'Ein Spaziergang an der frischen Luft kann sehr wohltuend sein.',
    exampleTranslation: 'A walk in the fresh air can be very beneficial.',
  },
  Entscheidend: {
    partOfSpeech: 'adjective',
    meaning: 'crucial; decisive',
    contextSentence: 'Entscheidend ist, dass wir auf unsere eigenen Bedürfnisse hören.',
    contextTranslation: 'What matters most is that we listen to our own needs.',
  },
  dazuzugehören: {
    partOfSpeech: 'verb',
    meaning: 'to belong; to be included',
    contextSentence: 'Sie geben uns Unterstützung und das Gefühl, dazuzugehören.',
    contextTranslation: 'They give us support and the feeling of belonging.',
  },
}
