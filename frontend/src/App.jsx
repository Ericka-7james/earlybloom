import { BrowserRouter, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Jobs from "./pages/Jobs";

/**
 * Renders the top-level application shell.
 *
 * This component is responsible for:
 * - configuring client-side routing
 * - rendering the shared navigation bar
 * - providing a consistent page container for all screens
 *
 * Future pages such as Jobs, Tracker, and Resume Upload can be added
 * to the routing table here without changing the overall layout.
 *
 * @returns {JSX.Element} The full application router and shell.
 */
function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />

        <main className="page-shell">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/jobs" element={<Jobs />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;