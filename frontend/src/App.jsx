import { BrowserRouter, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";

/**
 * Renders the top-level application shell.
 *
 * This component is responsible for:
 * - configuring client-side routing
 * - rendering the shared navigation bar
 * - providing a consistent page container for all screens
 *
 * Routes currently included:
 * - Home
 * - Jobs
 * - Sign In
 * - Sign Up
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
            <Route path="/sign-in" element={<SignIn />} />
            <Route path="/sign-up" element={<SignUp />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;