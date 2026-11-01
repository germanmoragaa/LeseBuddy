import { Route, Routes } from 'react-router'

import { Home } from '../features/dashboard/Home'
import { AddText } from '../features/reader/AddText'
import { Reader } from '../features/reader/Reader'
import { Flashcards } from '../features/review/Flashcards'
import { Vocabulary } from '../features/vocabulary/Vocabulary'
import { Progress } from '../features/progress/Progress'
import { AppShell } from './AppShell'

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Home />} />
        <Route path="/vocabulary" element={<Vocabulary />} />
        <Route path="/progress" element={<Progress />} />
      </Route>
      <Route path="/reader" element={<Reader />} />
      <Route path="/reader/new" element={<AddText />} />
      <Route path="/flashcards" element={<Flashcards />} />
    </Routes>
  )
}
