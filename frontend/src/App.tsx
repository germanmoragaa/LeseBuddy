import { ApiStatus } from './components/ApiStatus'

function App() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-white px-4 text-center">
      <h1 className="text-4xl font-bold text-gray-900">LeseBuddy</h1>
      <p className="max-w-md text-gray-600">
        Read authentic German. Understand more. Remember what you learn.
      </p>
      <ApiStatus />
    </main>
  )
}

export default App
