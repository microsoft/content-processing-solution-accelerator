import React, { useEffect, useState } from 'react'
import { JsonEditor, JsonEditorProps, githubDarkTheme } from 'json-edit-react'
import './JSONEditor.styles.scss'

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { fetchContentJsonData, setModifiedResult } from '../../store/slices/centerPanelSlice';

import { SearchBox } from "@fluentui/react-components";

interface JSONEditorProps {
  processId?: string | null;
}

const JSONEditor: React.FC<JSONEditorProps> = () => {
  const [jsonData, setJsonData] = React.useState({})
  const [isFocused, setIsFocused] = useState(false);
  const dispatch = useDispatch<AppDispatch>();
  const [searchText, setSearchText] = useState('');
  const searchBoxRef = React.useRef<HTMLDivElement | null>(null);

  const store = useSelector((state: RootState) => ({
    processId: state.leftPanel.processId,
    contentData: state.centerPanel.contentData,
    cLoader: state.centerPanel.cLoader,
    cError: state.centerPanel.cError,
    isJSONEditorSearchEnabled: state.centerPanel.isJSONEditorSearchEnabled
  }), shallowEqual);


  useEffect(() => {
    if (!store.cLoader) {
      if (Object.keys(store.contentData).length > 0) {
        const formattedJson = store.contentData.result;
        const data = {
          ...formattedJson
        }
        setJsonData(data);
      } else {
        setJsonData({})
      }
    }

  }, [store.contentData])

  const onUpdateHandle = (newData: any) => {
    dispatch(setModifiedResult(newData));
  }

  const handleFocus = () => setIsFocused(true);
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const newFocusTarget = e.relatedTarget as HTMLElement | null;
    if (
      searchBoxRef.current &&
      newFocusTarget &&
      searchBoxRef.current.contains(newFocusTarget)
    ) {
      return;
    }

    setIsFocused(false);
  };

  return (
    <>{
      store.cLoader ? <div className={"JSONEditorLoader"}><p>Loading...</p></div> :
        Object.keys(jsonData).length == 0 ? <p style={{ textAlign: 'center' }}>No data available</p> :
          <div className="JSONEditor-container">
            {store.isJSONEditorSearchEnabled &&
              <div className="JSONEditor-searchDiv">
                <div style={{ display: 'flex', justifyContent: 'flex-end' }} ref={searchBoxRef}>
                  <SearchBox
                    size="small"
                    placeholder="Search"
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    value={searchText}
                    onChange={(e, data) => { setIsFocused(true); setSearchText(data.value) }}
                    style={{
                      width: isFocused ? '200px' : '100px',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div></div>}
            <div className="JSONEditor-contentDiv">
              <JsonEditor
                data={jsonData}
                className='JSONEditorClass'
                rootName="extracted_result"
                searchText={searchText}
                searchFilter={"all"}
                searchDebounceTime={300}
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
                onUpdate={({ newData, currentData, newValue, currentValue, name, path }) => {
                  onUpdateHandle(newData)
                }}
                //setData={ setJsonData } // optional
                // restrictEdit={({ key, path, level, index, value, size, parentData, fullData, collapsed }) => {
                //   return !path.includes('extracted_result')
                // }
                // }
                restrictDelete={true}
              />
            </div>
          </div>
    }</>
  )
}

export default JSONEditor;

