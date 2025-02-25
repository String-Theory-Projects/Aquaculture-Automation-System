import React from 'react';
import PropTypes from 'prop-types';
import Navbar from './Navbar';
import './MainLayout.css';

const MainLayout = ({ children, title }) => {
  return (
    <div className="main-layout">
      <Navbar />
      <main className="main-content">
        {title && <h1 className="page-title">{title}</h1>}
        {children}
      </main>
      <footer className="footer">
        <div className="footer-content">
          <p>© {new Date().getFullYear()} Future Fish Agrotech. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
};

MainLayout.propTypes = {
  children: PropTypes.node.isRequired,
  title: PropTypes.string
};

export default MainLayout;