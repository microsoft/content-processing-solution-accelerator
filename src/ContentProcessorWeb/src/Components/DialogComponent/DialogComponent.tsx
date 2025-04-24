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
            {/* Render the footer buttons dynamically */}
            {footerButtons.map((button, index) => (
              <Button
                key={index}
                appearance={button.appearance}
                onClick={() => {
                  button.onClick();
                  onDialogClose(); // Close the dialog after an action
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
