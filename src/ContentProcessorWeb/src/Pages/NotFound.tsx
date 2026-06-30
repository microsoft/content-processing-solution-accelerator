// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * 404 Not Found page displayed when the user navigates to an unknown route.
 * Renders a friendly message with a whale emoji and a "Go home" button.
 */

import * as React from "react";
import {
  Button,
  Subtitle1,
} from "@fluentui/react-components";

/**
 * Renders a centered 404 page with a playful whale illustration.
 */
const NotFound: React.FC = () => {
  return (
    <div className="layout" style={{ display: "flex" }}>
      <div style={{ margin: "auto", textAlign: "center" }}>
        <img
          src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Animals/Whale.png"
          alt="Whale"
          width="64"
          height="64"
        />
        <br />
        <br />
        <Subtitle1>Whale hello there, may I kelp you?</Subtitle1>
        <br />
        <p style={{ fontSize: '.9rem', color: 'var(--colorNeutralForeground3)' }}>
          The page you are looking for doesn't exist. Let's get you back to dry
          land.
        </p>
        <br />
        <Button>Go home</Button>
      </div>
    </div>
  );
};

export default NotFound;
