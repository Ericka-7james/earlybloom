import { BrowserRouter, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Jobs from "./pages/Jobs";
import Tracker from "./pages/Tracker";
import Profile from "./pages/Profile";
import LearnMore from "./pages/LearnMore";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";

/**
 * Shared application route definitions.
 *
 * Keeping route metadata together makes the shell easier to maintain
 * without changing routing behavior.
 */
const APP_ROUTES = [
  { path: "/", element: <Home /> },
  { path: "/jobs", element: <Jobs /> },
  { path: "/tracker", element: <Tracker /> },
  { path: "/profile", element: <Profile /> },
  { path: "/learn-more", element: <LearnMore /> },
  { path: "/sign-in", element: <SignIn /> },
  { path: "/sign-up", element: <SignUp /> },
];

/**
 * Renders the top-level EarlyBloom application shell.
 *
 * Responsibilities:
 * - configure client-side routing
 * - render the shared navigation shell
 * - provide the primary page region
 *
 * This stays intentionally low-risk:
 * - routes are preserved
 * - page business logic is unchanged
 * - structure is made easier to maintain
 *
 * @returns {JSX.Element} The full routed application shell.
 */
function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />

        <main className="app-main" id="main-content">
          <div className="app-page-shell">
            <Routes>
              {APP_ROUTES.map((route) => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={route.element}
                />
              ))}
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;