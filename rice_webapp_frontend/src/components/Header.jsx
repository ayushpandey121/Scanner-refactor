import { RxHamburgerMenu } from "react-icons/rx";
import logo from "../assets/logo.png";
import "../styles/Header.css";
import { useNavigate } from "react-router-dom";
import "../styles/Constant.css";
import React, { useState } from "react";
import { generateHardwareId } from "../utils/hardwareId";

// Header receives sidebar control props
function Header({ showSidebar, setShowSidebar }) {
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const toggleSideBar = () => setShowSidebar(!showSidebar);

  const handleLogoClick = () => {
    navigate('/landing');
  };

  const handleLogout = async () => {
    if (loggingOut) return; // Prevent multiple clicks
    
    setLoggingOut(true);
    
    try {
      console.log('Logging out...');
      
      // Get hardware ID
      const hardwareId = await generateHardwareId();
      
      // Call logout endpoint to update S3
      const response = await fetch('http://43.205.7.195:8084/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ hardwareId })
      });

      const data = await response.json();

      if (data.success) {
        console.log('✅ Logout successful - S3 updated with loggedIn: false');
        
        // Clear localStorage cache
        localStorage.removeItem('isActivated');
        localStorage.removeItem('hardwareId');
        localStorage.removeItem('deviceId');
        localStorage.removeItem('username');
        
        // Force navigation to activation page and reload
        navigate('/', { replace: true });
        
        // Small delay to ensure navigation completes before reload
        setTimeout(() => {
          window.location.reload();
        }, 100);
      } else {
        console.error('Logout failed:', data.message);
        alert('Logout failed. Please try again.');
        setLoggingOut(false);
      }
    } catch (error) {
      console.error('Logout error:', error);
      alert('Network error during logout. Please try again.');
      setLoggingOut(false);
    }
  };

  return (
    <div className="header-container">
      <div className="left-section">
        {/* Hamburger at far-left */}
        <RxHamburgerMenu
          className="hamburger-icon header-hamburger"
          onClick={toggleSideBar}
        />
        <img 
          src={logo} 
          alt="Logo" 
          className="header-logo" 
          onClick={handleLogoClick} 
          style={{ cursor: 'pointer' }} 
        />
      </div>
      <p className="app-title">Agsure Rice Grain Analyser</p>
      <button 
        className="logout-button" 
        onClick={handleLogout}
        disabled={loggingOut}
      >
        {loggingOut ? 'Logging out...' : 'Logout'}
      </button>
    </div>
  );
}

export default Header;