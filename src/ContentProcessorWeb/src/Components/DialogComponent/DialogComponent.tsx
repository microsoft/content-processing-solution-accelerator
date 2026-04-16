// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Reusable confirmation dialog built on Fluent UI v9 Dialog primitives.
 * Renders a title, content body, and a dynamic set of footer action buttons.
 */

import * as React from "react";
import {
  Dialog,
  DialogSurface,
  DialogTitle,
  DialogBody,
  DialogContent,
  DialogActions,
  Button,
  useId,
} from "@fluentui/react-components";

import { ConfirmationProps } from './DialogComponentTypes'


/**
 * Renders a modal confirmation dialog with configurable title, content, and action buttons.
 */
export const Confirmation: React.FC<ConfirmationProps> = ({
  title,
  content,
  isDialogOpen,
  onDialogClose,
  footerButtons,
}) => {
  const dialogId = useId("dialog-");

  return (
    <Dialog open={isDialogOpen} onOpenChange={onDialogClose}>
      <DialogSurface
        aria-labelledby={`${dialogId}-title`}
        aria-describedby={`${dialogId}-content`}
      >
        <DialogBody>
          <DialogTitle id={`${dialogId}-title`}>{title}</DialogTitle>
          <DialogContent id={`${dialogId}-content`}>{content}</DialogContent>
          <DialogActions>
            {footerButtons.map((button, index) => (
              <Button
                key={index}
                appearance={button.appearance}
                onClick={() => {
                  button.onClick();
                  onDialogClose();
                }}
              >
                {button.text}
              </Button>
            ))}
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
};
