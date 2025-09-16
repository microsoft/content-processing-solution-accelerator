import React, { useCallback, useEffect, useState, useRef } from "react";
import { Accordion, AccordionItem, AccordionHeader, AccordionPanel, tokens } from "@fluentui/react-components";
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState, AppDispatch } from '../../../../store/index.ts';
import { JsonEditor } from "json-edit-react";
import { CheckmarkCircleFilled } from "@fluentui/react-icons";
import { Spinner } from "@fluentui/react-components";

type LoadingStates = {
  [key: string]: boolean;
};

const ProcessSteps = () => {
  const status = ['extract', 'processing', 'map', 'evaluate'];
  const [loadingStates, setLoadingStates] = useState<LoadingStates>({});
  const childRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});


  const store = useSelector((state: RootState) => ({
    processStepsData: state.centerPanel.processStepsData,
    selectedItem: state.leftPanel.selectedItem,
  }), shallowEqual
  );

  const hasValidSelection = !!store.selectedItem && !!store.selectedItem.process_id;
  const hasProcessStepsData = Array.isArray(store.processStepsData) && store.processStepsData.length > 0;

  const renderProcessTimeInSeconds = (timeString: string) => {
    if (!timeString) {
      return timeString;
    }
    const parts = timeString.split(":");
    if (parts.length !== 3) {
      return timeString;
    }
    const [hours, minutes, seconds] = parts.map(Number);
    const totalSeconds = (hours * 3600 + minutes * 60 + seconds).toFixed(2);
    return `${totalSeconds}s`;
  };

  const handleExpand = (itemId: any) => {
    setLoadingStates((prevState) => ({ ...prevState, [itemId]: true }));
    setTimeout(() => {
      const childDiv = childRefs.current[itemId];
      if (childDiv) {
        childDiv.classList.add('loaded');
      }
    }, 500);

  };

  useEffect(() => {
    const observers: MutationObserver[] = [];
    Object.keys(childRefs.current).forEach((itemId) => {
      const childDiv = childRefs.current[itemId];
      if (childDiv) {
        const observer = new MutationObserver(() => {
          if (childDiv.classList.contains('loaded')) {
            setLoadingStates((prevState) => ({ ...prevState, [itemId]: false }));
          }
        });
        observer.observe(childDiv, { attributes: true, attributeFilter: ['class'] });
        observers.push(observer);
      }
    });
    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, []);

  if (!hasValidSelection || !hasProcessStepsData) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
        No data available.
      </div>
    );
  }

  return (
    <Accordion collapsible>
      {!status.includes(store.selectedItem.status) && store.processStepsData?.map((step, index) => (
        <AccordionItem key={index} value={step.step_name}>
          <AccordionHeader onClick={() => handleExpand(index)}> {loadingStates[index] && <Spinner size="tiny" style={{ position: 'absolute', left: '10px' }} label="" />}
            <span style={{ fontWeight: 'bold', textTransform: 'capitalize'}}>{step.step_name}</span>
            <span style={{ color: 'green', marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
              {renderProcessTimeInSeconds(step.processed_time)} <CheckmarkCircleFilled style={{ marginLeft: '4px' }} />
            </span>
          </AccordionHeader>
          <div ref={(el) => (childRefs.current[index] = el)}>
            <AccordionPanel >
              <JsonEditor
                key={`json-editor-${index}`}
                data={step}
                collapse={5}
                restrictEdit={true}
                restrictDelete={true}
                restrictAdd={true}
                rootName={step.step_name.toLowerCase()}
                collapseAnimationTime={300}
                theme={[{
                  styles: {
                    container: {
                      width: '89%',
                      minWidth: '100%',
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif',
                      fontSize: '14px',
                      paddingTop: '0px'
                    },
                  }
                }]}
              />
            </AccordionPanel>
          </div>
        </AccordionItem>
      ))}
    </Accordion>

  );
};

export default ProcessSteps;
