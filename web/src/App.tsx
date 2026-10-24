import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { useAuth } from "./lib/auth";
import { AskPage } from "./pages/AskPage";
import { BrowsePage } from "./pages/BrowsePage";
import { CalendarPage } from "./pages/CalendarPage";
import { EntryPage } from "./pages/EntryPage";
import { LoginPage } from "./pages/LoginPage";
import { ReviewPage } from "./pages/ReviewPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated, loading } = useAuth();
  if (loading) {
    return <p className="footnote" style={{ padding: 24 }}>Loading…</p>;
  }
  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<CalendarPage />} />
        <Route path="browse" element={<BrowsePage />} />
        <Route path="ask" element={<AskPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="entry/:id" element={<EntryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
