
import { ReactNode } from 'react';

interface FooterButton {
  text: string;
  appearance: "primary" | "secondary";
  onClick: () => void;
}

export interface ConfirmationProps {
  title: string;
  content: string | ReactNode;
  isDialogOpen: boolean; // Controlled state for dialog visibility
  onDialogClose: () => void; // Function to close the dialog
  footerButtons: FooterButton[]; // Array of footer buttons
}