import { Route, Routes } from 'react-router'

import { Home } from '../features/dashboard/Home'
import { Login } from '../features/auth/Login'
import { Signup } from '../features/auth/Signup'
import { VerifyEmail } from '../features/auth/VerifyEmail'
import { Welcome } from '../features/auth/Welcome'
import { AddText } from '../features/reader/AddText'
import { Reader } from '../features/reader/Reader'
import { Flashcards } from '../features/review/Flashcards'
import { Vocabulary } from '../features/vocabulary/Vocabulary'
import { Progress } from '../features/progress/Progress'
import { AppShell } from './AppShell'
import { ProtectedRoute } from './ProtectedRoute'
import { PublicOnlyRoute } from './PublicOnlyRoute'
import { RequireUnverifiedRoute } from './RequireUnverifiedRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
      </Route>

      <Route element={<RequireUnverifiedRoute />}>
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/app" element={<Home />} />
          <Route path="/app/vocabulary" element={<Vocabulary />} />
          <Route path="/app/progress" element={<Progress />} />
        </Route>
        <Route path="/app/reader" element={<Reader />} />
        <Route path="/app/reader/new" element={<AddText />} />
        <Route path="/app/flashcards" element={<Flashcards />} />
      </Route>
    </Routes>
  )
}
