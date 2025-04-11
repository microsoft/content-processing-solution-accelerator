import React from 'react';
import { CaretUp16Filled, CaretDown16Filled, EditPersonFilled } from '@fluentui/react-icons';
import { Button, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem } from '@fluentui/react-components';
import { MoreVerticalRegular, MoreVerticalFilled, bundleIcon , Delete20Filled , Delete20Regular} from '@fluentui/react-icons';

type CellRendererProps = {
  type: string;
  props?: any;
};

const MoreVerticallIcon = bundleIcon(
  MoreVerticalFilled,
  MoreVerticalRegular
);

const DeleteIcon = bundleIcon(
  Delete20Filled,
  Delete20Regular
);

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
  const renderText = (text: any, type = '') => {
    if (type === 'date') {
      const date = new Date(text);
      const formattedDate = `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}/${date.getFullYear()}`;
      return <div className="columnCotainer centerAlign">{formattedDate}</div>;
    }
    return <div className={type === 'center' ? 'columnCotainer centerAlign' : 'columnCotainer'}>{text}</div>;
  };

  // Render for delete button
  const renderDeleteButton = (item: any, deleteBtnStatus: any) => (
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
              setSelectedDeleteItem(item);
              toggleDialog();
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
      return renderText(text, 'center');
    case 'date':
      return renderText(text, 'date');
    case 'deleteButton':
      return renderDeleteButton(item, deleteBtnStatus || {});
    default:
      return <div>Invalid Type</div>;
  }
};

export default CellRenderer;
