// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Factory component that renders grid cells in different formats
 * (status badges, percentages, process times, delete buttons, etc.)
 * based on a `type` discriminator string.
 */

import React from 'react';
import { CaretUp16Filled, CaretDown16Filled, EditPersonFilled } from '@fluentui/react-icons';
import { Button, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem } from '@fluentui/react-components';
import { MoreVerticalRegular, MoreVerticalFilled, bundleIcon, Delete20Filled, Delete20Regular } from '@fluentui/react-icons';

/** Props describing a delete-button disabled state. */
interface DeleteBtnStatus {
  /** Whether the button is disabled. */
  readonly disabled: boolean;
  /** Tooltip message shown when disabled. */
  readonly message: string;
}

/** Minimal item shape expected by the delete button renderer. */
interface DeleteItem {
  readonly processId: { readonly label: string };
}

/** Union of all possible cell renderer prop bags. */
interface CellRendererExtraProps {
  readonly txt?: string;
  readonly timeString?: string;
  readonly valueText?: string;
  readonly status?: string;
  readonly lastModifiedBy?: string;
  readonly text?: string | number;
  readonly item?: DeleteItem;
  readonly deleteBtnStatus?: DeleteBtnStatus;
  readonly setSelectedDeleteItem?: (item: DeleteItem) => void;
  readonly toggleDialog?: () => void;
}

/** Props for the {@link CellRenderer} component. */
interface CellRendererProps {
  /** Determines which cell rendering strategy to use. */
  readonly type: string;
  /** Extra data required by the selected rendering strategy. */
  readonly props?: CellRendererExtraProps;
}

const MoreVerticallIcon = bundleIcon(
  MoreVerticalFilled,
  MoreVerticalRegular
);

const DeleteIcon = bundleIcon(
  Delete20Filled,
  Delete20Regular
);

/**
 * Renders a table cell in different visual formats based on the `type` prop.
 */
const CellRenderer: React.FC<CellRendererProps> = ({ type, props }) => {
  // Destructure props based on type
  const {
    txt, timeString, valueText, status, lastModifiedBy, text, item, deleteBtnStatus, setSelectedDeleteItem, toggleDialog,
  } = props || {};

  // Render for rounded button
  const renderRoundedButton = (txt: string) => (
    <div title={txt} className="roundedBtn">
      <span className={txt === 'Processed' ? 'ProcessedCls' : ''}>{txt}</span>
    </div>
  );

  // Render for processing time
  const renderProcessTimeInSeconds = (timeString: string) => {
    if (!timeString) {
      return <div className="columnCotainer centerAlign">...</div>;
    }

    const parts = timeString.split(":");
    if (parts.length !== 3) {
      return <div className="columnCotainer centerAlign">{timeString}</div>;
    }

    const [hours, minutes, seconds] = parts.map(Number);
    const totalSeconds = (hours * 3600 + minutes * 60 + seconds).toFixed(2);

    return <div className="columnCotainer centerAlign">{totalSeconds}s</div>;
  };

  // Render for percentage
  const renderPercentage = (valueText: string, status: string) => {
    const decimalValue = Number(valueText);
    if (isNaN(decimalValue) || status !== 'Completed') {
      return <div className="percentageContainer"><span className="textClass">...</span></div>;
    }

    const wholeValue = Math.round(decimalValue * 100);
    let numberClass = '';

    // Apply color based on value
    if (wholeValue > 80) {
      numberClass = 'gClass';
    } else if (wholeValue >= 50 && wholeValue <= 80) {
      numberClass = 'yClass';
    } else if (wholeValue >= 30 && wholeValue < 50) {
      numberClass = 'oClass';
    } else {
      numberClass = 'rClass';
    }

    return (
      <div className="percentageContainer">
        <span className={numberClass}>{wholeValue}%</span>
        {wholeValue > 50 ? (
          <CaretUp16Filled className={numberClass} />
        ) : (
          <CaretDown16Filled className={numberClass} />
        )}
      </div>
    );
  };

  // Render for schema score
  const calculateSchemaScore = (valueText: string, lastModifiedBy: string, status: string) => {
    if (lastModifiedBy === 'user') {
      return (
        <div className="percentageContainer">
          <EditPersonFilled className="editPersonIcon" />
          <span className="textClass">
            Verified
          </span>
        </div>
      );
    }
    return renderPercentage(valueText, status);
  };

  // Render for text
  const renderText = (text: string | number, type = '') => {
    if (type === 'date') {
      const date = new Date(text);
      const formattedDate = `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}/${date.getFullYear()}`;
      return <div className="columnCotainer centerAlign">{formattedDate}</div>;
    }
    return <div className={type === 'center' ? 'columnCotainer centerAlign' : 'columnCotainer'}>{text}</div>;
  };

  // Render for delete button
  const renderDeleteButton = (item: DeleteItem, deleteBtnStatus: DeleteBtnStatus) => (
    <Menu positioning={{ autoSize: true }} key={item.processId.label}>
      <MenuTrigger>
        <Button
          disabled={deleteBtnStatus.disabled}
          icon={<MoreVerticallIcon />}
          appearance="subtle"
          aria-label="More actions"
          title={deleteBtnStatus.message}
          style={{ minWidth: 'auto' }}
        />
      </MenuTrigger>

      <MenuPopover style={{ maxWidth: 'auto', minWidth: '80px' }} >
        <MenuList style={{ maxWidth: 'auto', minWidth: 'auto' }}>
          <MenuItem
            icon={<DeleteIcon />}
            onClick={() => {
              setSelectedDeleteItem?.(item);
              toggleDialog?.();
            }}
            style={{ maxWidth: 'auto', minWidth: 'auto' }}
          >
            Delete
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );

  // Switch based on type
  switch (type) {
    case 'roundedButton':
      return renderRoundedButton(txt || '');
    case 'processTime':
      return renderProcessTimeInSeconds(timeString || '');
    case 'percentage':
      return renderPercentage(valueText || '', status || '');
    case 'schemaScore':
      return calculateSchemaScore(valueText || '', lastModifiedBy || '', status || '');
    case 'text':
      return renderText(text ?? '', 'center');
    case 'date':
      return renderText(text ?? '', 'date');
    case 'deleteButton':
      return item ? renderDeleteButton(item, deleteBtnStatus || { disabled: false, message: '' }) : <div>Invalid Type</div>;
    default:
      return <div>Invalid Type</div>;
  }
};

export default CellRenderer;
