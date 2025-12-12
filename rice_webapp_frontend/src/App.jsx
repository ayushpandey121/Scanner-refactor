import { useState, useEffect } from "react";
import Result from "./components/Result";
import Header from "./components/Header";
import Upload from "./components/Upload";
import GrainGallery from "./components/GrainGallery";
import { Routes, Route, useLocation, Navigate } from "react-router-dom";
import RiceAnalysis from "./components/RiceAnalysis";
import Sidebar from "./components/Sidebar";
import ActivationPage from "./components/ActivationPage";
import Details from "./components/Details";
import LandingPage from "./components/LandingPage";
import ReportPage from "./components/ReportPage";
import UpdateNotification from "./components/Notification";
import { generateHardwareId } from "./utils/hardwareId";
import Settings from "./components/Settings";
import { CiSettings } from "react-icons/ci";
import "./styles/App.css";

function App() {
  const [showSidebar, setShowSidebar] = useState(true);
  const [isActivated, setIsActivated] = useState(false);
  const [activationChecked, setActivationChecked] = useState(false);
  const location = useLocation();

  // Check activation status on app load
  useEffect(() => {
    const checkActivation = async () => {
      try {
        console.log('Checking activation and login status from S3...');

        // Generate current hardware ID
        const currentHardwareId = await generateHardwareId();
        console.log('Current Hardware ID:', currentHardwareId);

        // Check login status with EC2 (which checks S3)
        try {
          const response = await fetch('http://43.205.7.195:8084/check-login-status', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ hardwareId: currentHardwareId })
          });

          if (response.ok) {
            const data = await response.json();

            if (data.success && data.loggedIn) {
              console.log('✅ User is logged in');
              console.log('Device ID:', data.deviceId);
              console.log('Username:', data.username);

              // Log expiration date if available
              // if (data.expirationDate) {
              //   console.log('Expiration date:', data.expirationDate);
              // }

              // Cache data in localStorage for quick reference only
              localStorage.setItem('isActivated', 'true');
              localStorage.setItem('hardwareId', currentHardwareId);
              localStorage.setItem('deviceId', data.deviceId);
              localStorage.setItem('username', data.username);
              localStorage.setItem('length_correction', data.length_correction);
              localStorage.setItem('wi_correction', data.wi_correction);
              localStorage.setItem('ww_correction', data.ww_correction);

              // // Store expiration date if available
              // if (data.expirationDate) {
              //   localStorage.setItem('expirationDate', data.expirationDate);
              // }

              setIsActivated(true);
              setActivationChecked(true);
              return;
            } else {
              console.log('❌ User is not logged in or not activated');

              // Check if it's an expiration error (HTTP 403)
              if (response.status === 403) {
                console.log('❌ Activation key has expired');
              }
            }
          } else {
            console.log('Failed to check login status:', response.status);

            // Check if it's an expiration error
            if (response.status === 403) {
              console.log('❌ Activation key has expired');
            }
          }
        } catch (error) {
          console.error('Error checking login status:', error);
        }

        // If we reach here, user is not logged in
        console.log('❌ Not activated/logged in - Clearing cache and showing activation page');

        // Clear any stale localStorage data
        localStorage.removeItem('isActivated');
        localStorage.removeItem('hardwareId');
        localStorage.removeItem('deviceId');
        localStorage.removeItem('username');
        // localStorage.removeItem('expirationDate');

        setIsActivated(false);
        setActivationChecked(true);

      } catch (error) {
        console.error('Critical error checking activation:', error);

        // On critical error, assume not activated for security
        localStorage.removeItem('isActivated');
        localStorage.removeItem('hardwareId');
        localStorage.removeItem('deviceId');
        localStorage.removeItem('username');
        // localStorage.removeItem('expirationDate');

        setIsActivated(false);
        setActivationChecked(true);
      }
    };

    checkActivation();
  }, []);

  // Auto-toggle sidebar based on screen width
  useEffect(() => {
    const applyResponsiveSidebar = () => {
      if (window.innerWidth <= 768) {
        setShowSidebar(false);
      } else {
        setShowSidebar(true);
      }
    };
    applyResponsiveSidebar();
    window.addEventListener("resize", applyResponsiveSidebar);
    return () => window.removeEventListener("resize", applyResponsiveSidebar);
  }, []);

  // Determine if header and sidebar should be shown based on current route
  const noHeaderRoutes = ['/', '/landing'];
  const noSidebarRoutes = ['/', '/landing'];
  const showHeader = activationChecked && isActivated && !noHeaderRoutes.includes(location.pathname);
  const shouldShowSidebar = activationChecked && !noSidebarRoutes.includes(location.pathname);

  return (
    <div className={`app-wrapper ${showHeader ? '' : 'no-header'}`}>
      {showHeader && (
        <Header showSidebar={showSidebar} setShowSidebar={setShowSidebar} />
      )}
      <div className="main-container">
        {shouldShowSidebar && (
          <Sidebar showSidebar={showSidebar} setShowSidebar={setShowSidebar} />
        )}
        <div className="content-area">
          {activationChecked ? (
            <Routes>
              <Route path="/" element={isActivated ? <Navigate to="/landing" replace /> : <ActivationPage />} />
              <Route path="/landing" element={isActivated ? <LandingPage /> : <Navigate to="/" replace />} />
              <Route path="/upload" element={isActivated ? <Upload /> : <Navigate to="/" replace />} />
              <Route path="/results" element={isActivated ? <Result /> : <Navigate to="/" replace />} />
              <Route path="/details" element={isActivated ? <Details /> : <Navigate to="/" replace />} />
              <Route path="/settings" element={isActivated ? <Settings /> : <Navigate to="/" replace />} />
              <Route path="/gallery" element={isActivated ? <GrainGallery /> : <Navigate to="/" replace />} />
              <Route path="/analysis" element={isActivated ? <RiceAnalysis /> : <Navigate to="/" replace />} />
              <Route path="/report" element={isActivated ? <ReportPage /> : <Navigate to="/" replace />} />
            </Routes>
          ) : (
            <div>Loading...</div>
          )}
        </div>
      </div>

      {/* Update Notification - Shows on all pages when update is available */}
      <UpdateNotification />
    </div>
  );
}

export default App;