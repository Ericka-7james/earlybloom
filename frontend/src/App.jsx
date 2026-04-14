import { BrowserRouter, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import Tracker from "./pages/Tracker";
import LearnMore from "./pages/LearnMore";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";

/**
 * Renders the top-level application shell.
 *
 * This component is responsible for:
 * - configuring client-side routing
 * - rendering the shared navigation bar
 * - providing a consistent product-page shell
 *
 * Routes currently included:
 * - Home
 * - Jobs
 * - Tracker
 * - Learn More
 * - Sign In
 * - Sign Up
 *
 * Future-ready:
 * - shell supports adding /profile later without restructuring
 *
 * @returns {JSX.Element} The full application router and shell.
 */
function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />

        <main className="page-shell app-page-shell">
          <div className="app-page-frame">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/tracker" element={<Tracker />} />
              <Route path="/learn-more" element={<LearnMore />} />
              <Route path="/sign-in" element={<SignIn />} />
              <Route path="/sign-up" element={<SignUp />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;