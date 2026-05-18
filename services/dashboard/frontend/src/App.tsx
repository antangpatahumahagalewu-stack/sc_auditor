import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import Dashboard from './pages/Dashboard';
import Audits from './pages/Audits';
import AuditDetail from './pages/AuditDetail';
import Programs from './pages/Programs';
import ProgramDetail from './pages/ProgramDetail';
import Settings from './pages/Settings';
import Metrics from './pages/Metrics';
import Daemon from './pages/Daemon';
import Updates from './pages/Updates';
import Feedback from './pages/Feedback';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/audits" element={<Audits />} />
          <Route path="/audits/:id" element={<AuditDetail />} />
          <Route path="/programs" element={<Programs />} />
          <Route path="/programs/:slug" element={<ProgramDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/daemon" element={<Daemon />} />
          <Route path="/updates" element={<Updates />} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
