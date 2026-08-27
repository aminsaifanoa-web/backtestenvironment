import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import NewExperiment from './pages/NewExperiment'
import Experiments from './pages/Experiments'
import ExperimentDetail from './pages/ExperimentDetail'
import StrategyLibrary from './pages/StrategyLibrary'
import Leaderboard from './pages/Leaderboard'
import DataQuality from './pages/DataQuality'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<NewExperiment />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/experiments/:id" element={<ExperimentDetail />} />
          <Route path="/library" element={<StrategyLibrary />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
