// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Schema selection dropdown that populates from the Redux store and
 * dispatches the selected schema option for filtering content processing.
 */

import React, { useState, useEffect } from "react";
import { Combobox, makeStyles, Option, useId } from "@fluentui/react-components";
import type { ComboboxProps } from "@fluentui/react-components";

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../../../store';
import { setSchemaSelectedOption, fetchSchemasBySchemaSet } from '../../../../store/slices/leftPanelSlice';

import { OptionList } from './SchemaDropdownTypes';

import './SchemaDropdown.styles.scss';

const useStyles = makeStyles({
  root: {
    display: "grid",
    gridTemplateRows: "repeat(1fr)",
    justifyItems: "stretch",
    gap: "2px",
    flex: "1 1 125px",
    minWidth: "0px",
  },
});

/**
 * Renders a clearable Combobox dropdown populated with schema sets from the store.
 */
const ComboboxComponent = (props: Partial<ComboboxProps>) => {
  const comboId = useId("combo-default");
  const styles = useStyles();

  const [options, setOptions] = useState<OptionList[]>([]);

  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector(
    (state: RootState) => ({
      schemaData: state.leftPanel.schemaData,
      schemaSetData: state.leftPanel.schemaSetData,
      schemaSelectedOption: state.leftPanel.schemaSelectedOption,
      schemaError: state.leftPanel.schemaError,
    }),
    shallowEqual
  );

  useEffect(() => {
    setOptions(
      store.schemaSetData
        .map((item) => ({
          key: typeof item.Id === 'string' ? item.Id : '',
          value: typeof item.Name === 'string' ? item.Name : '',
        }))
        .filter((item) => item.key !== '' && item.value !== '')
    );
  }, [store.schemaSetData]);

  const handleChange: (typeof props)["onOptionSelect"] = (ev, data) => {
    const selectedItem = data.optionValue !== undefined ? data : {}
    dispatch(setSchemaSelectedOption(selectedItem));
    if (data.optionValue) {
      dispatch(fetchSchemasBySchemaSet({ schemaSetId: data.optionValue }));
    }
  };

  return (
    <div className={styles.root}>
      <Combobox
        id={`${comboId}-default`}
        aria-labelledby={comboId}
        placeholder="Select Collection"
        onOptionSelect={handleChange}
        {...props}
        clearable
        className="comboboxClass"
        autoComplete="off"
      >
        {options.map((option) => (
          <Option text={option.value} key={option.key} value={option.key}>
            {option.value}
          </Option>
        ))}
      </Combobox>
      {store.schemaError && <div>Error: {store.schemaError}</div>}
    </div>
  );
};

export default ComboboxComponent;
