// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Application header with navigation tabs, AI-content disclaimer badge,
 * and an authenticated user avatar menu with logout support.
 */

import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Header } from "../../Hooks/useHeaderHooks";
import {
  TabList,
  Tab,
  TabValue,
  Menu,
  MenuTrigger,
  MenuPopover,
  MenuList,
  MenuItem,
  MenuDivider,
  Avatar,
} from "@fluentui/react-components";
import { ArrowExit } from "../../Imports/bundleIcons";
import MainLogo from "../../Imports/MainLogo.svg";
import { DocumentBulletListCubeRegular, InfoRegular } from "@fluentui/react-icons";

import useAuth from "../../msal-auth/useAuth";
import { useSelector, shallowEqual } from 'react-redux';
import { RootState } from '../../store';
import useSwaggerPreview from "../../Hooks/useSwaggerPreview";

import "./Header.css";

/** Props for the {@link HeaderPage} component. */
interface HeaderPageProps {
  /** Callback to toggle between light and dark themes. */
  toggleTheme: () => void;
  /** Whether the UI is currently in dark mode. */
  isDarkMode: boolean;
}

const tabConfigs = [
  {
    icon: <DocumentBulletListCubeRegular />,
    value: "default",
    label: "Content",
  },
  {
    icon: <DocumentBulletListCubeRegular />,
    value: "api",
    label: "API Documentation",
  },
];

/**
 * Renders the top-level application header with site navigation, AI disclaimer, and user menu.
 */
const HeaderPage: React.FC<HeaderPageProps> = ({ toggleTheme, isDarkMode }) => {
  const { user, logout } = useAuth();

  const authEnabled = process.env.REACT_APP_AUTH_ENABLED?.toLowerCase() !== 'false';

  const { openSwaggerUI } = useSwaggerPreview();
  const store = useSelector((state: RootState) => ({
    swaggerJSON: state.leftPanel.swaggerJSON,
  }), shallowEqual);

  const navigate = useNavigate();
  const location = useLocation();

  const tabRoutes: { [key: string]: TabValue } = {
    "/home": "home",
    "/default": "default",
    "/auxiliary": "auxiliary",
  };

  // Get the current tab based on the route
  const currentTab =
    Object.keys(tabRoutes).find((route) =>
      location.pathname.startsWith(route)
    ) || "/home"; // Default to "home"

  const handleTabChange = (
    _: React.SyntheticEvent,
    data: { value: TabValue }
  ) => {
    if (data.value === 'api') {
      _.preventDefault(); 
      const apiUrl: string = process.env.REACT_APP_API_BASE_URL as string; 
      const token = localStorage.getItem('token') ?? undefined;
      openSwaggerUI(store.swaggerJSON, apiUrl, token)
    } else {
      const newRoute = Object.keys(tabRoutes).find(
        (key) => tabRoutes[key] === data.value
      );
      if (newRoute) {
        navigate(newRoute);
      }
    }

  };


  return (
    <Header
      avatarSrc={MainLogo}
      title="Content Processing"
      subtitle="Accelerator"
      badge=""
    >
      <div className="headerNav">
        <TabList
          selectedValue={tabRoutes[currentTab]}
          onTabSelect={handleTabChange}
          aria-label="Site Navigation Tabs"
          size="small"
        >
          {tabConfigs.map(({ icon, value, label }) => (
            <Tab key={value} icon={icon} value={value}>
              {label}
            </Tab>
          ))}
        </TabList>
      </div>
      <div className="headerTag">
        <InfoRegular style={{ marginRight: "4px" }} />
        <span>AI-generated content may be incorrect</span>
      </div>

      {/* Tools Section */}
      { authEnabled && 
        <div className="headerTools">
          <Menu hasIcons positioning={{ autoSize: true }}>
            <MenuTrigger disableButtonEnhancement>
              <Avatar
                color="colorful"
                name={user?.name}
                aria-label="App"
                className="clickable-avatar"
              />
            </MenuTrigger>
            <MenuPopover style={{ minWidth: "192px" }}>
              <MenuList>
                <MenuDivider />
                <MenuItem icon={<ArrowExit />} onClick={logout}>Logout</MenuItem>
              </MenuList>
            </MenuPopover>
          </Menu>
        </div>
      }
    </Header>
  );
};

export default HeaderPage;
