import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { usePond } from '../../context/PondContext';
import { FaUserCircle, FaCog, FaSignOutAlt, FaList, FaPlusCircle, FaHome, FaBars, FaTimes } from 'react-icons/fa';
import './Navbar.css';

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { user, logout } = useAuth();
  const { ponds, selectedPond, changePond } = usePond();
  const location = useLocation();
  const navigate = useNavigate();

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handlePondChange = (pond) => {
    changePond(pond);
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo and brand */}
        <div className="navbar-brand">
          <Link to="/">
            <img src="/src/assets/logo-light.svg" alt="Future Fish Logo" className="brand-logo" />
          </Link>
        </div>

        {/* Pond selector */}
        <div className="pond-selector">
          {ponds.length > 0 && selectedPond ? (
            <div className="dropdown">
              <button className="dropdown-toggle" onClick={toggleDropdown}>
                {selectedPond.name} <span className="caret"></span>
              </button>
              {isDropdownOpen && (
                <div className="dropdown-menu">
                  {ponds.map((pond) => (
                    <button
                      key={pond.id}
                      className={`dropdown-item ${selectedPond.id === pond.id ? 'active' : ''}`}
                      onClick={() => handlePondChange(pond)}
                    >
                      {pond.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="no-ponds">No ponds available</p>
          )}
        </div>

        {/* Mobile menu button */}
        <button className="navbar-toggler" onClick={toggleMenu}>
          {isMenuOpen ? <FaTimes /> : <FaBars />}
        </button>

        {/* Navigation links */}
        <div className={`navbar-collapse ${isMenuOpen ? 'show' : ''}`}>
          <ul className="navbar-nav">
            <li className={`nav-item ${location.pathname === '/' ? 'active' : ''}`}>
              <Link to="/" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                <FaHome className="nav-icon" />
                <span className="nav-text">Dashboard</span>
              </Link>
            </li>
            <li className={`nav-item ${location.pathname === '/register-pond' ? 'active' : ''}`}>
              <Link to="/register-pond" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                <FaPlusCircle className="nav-icon" />
                <span className="nav-text">Register Pond</span>
              </Link>
            </li>
            <li className={`nav-item ${location.pathname === '/manage-ponds' ? 'active' : ''}`}>
              <Link to="/manage-ponds" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                <FaList className="nav-icon" />
                <span className="nav-text">Manage Ponds</span>
              </Link>
            </li>
            <li className={`nav-item ${location.pathname === '/settings' ? 'active' : ''}`}>
              <Link to="/settings" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                <FaCog className="nav-icon" />
                <span className="nav-text">Settings</span>
              </Link>
            </li>
            <li className={`nav-item ${location.pathname === '/profile' ? 'active' : ''}`}>
              <Link to="/profile" className="nav-link" onClick={() => setIsMenuOpen(false)}>
                <FaUserCircle className="nav-icon" />
                <span className="nav-text">Profile</span>
              </Link>
            </li>
            <li className="nav-item">
              <button className="nav-link logout-btn" onClick={handleLogout}>
                <FaSignOutAlt className="nav-icon" />
                <span className="nav-text">Logout</span>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;