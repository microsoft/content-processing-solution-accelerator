import React, { useState, useEffect } from "react";
import { Combobox, makeStyles, Option, useId } from "@fluentui/react-components";
import type { ComboboxProps } from "@fluentui/react-components";
import './SchemaDropdown.styles.scss';
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState } from '../../../../store';
import { setSchemaSelectedOption } from '../../../../store/slices/leftPanelSlice';
import { OptionList, SchemaItem, StoreState } from './SchemaDropdownTypes';

const useStyles = makeStyles({
  root: {
    display: "grid",
    gridTemplateRows: "repeat(1fr)",
    justifyItems: "start",
    gap: "2px",
    flex: 1
  },
});

const ComboboxComponent = (props: Partial<ComboboxProps>) => {
  const comboId = useId("combo-default");
  const styles = useStyles();

  const [options, setOptions] = useState<OptionList[]>([]);

  const dispatch = useDispatch();

  const store = useSelector(
    (state: RootState) => ({
      schemaData: state.leftPanel.schemaData,
      schemaSelectedOption: state.leftPanel.schemaSelectedOption,
      schemaError: state.leftPanel.schemaError,
    }),
    shallowEqual
  );

  useEffect(() => {
    setOptions(
      store.schemaData.map((item: SchemaItem) => ({
        key: item.Id,
        value: item.Description,
      }))
    );
  }, [store.schemaData]);

  const handleChange: (typeof props)["onOptionSelect"] = (ev, data) => {
    const selectedItem = data.optionValue !=undefined ? data : {}
    dispatch(setSchemaSelectedOption(selectedItem));
  };

  return (
    <div className={styles.root}>
      <Combobox
        id={`${comboId}-default`}
        aria-labelledby={comboId}
        placeholder="Select Schema"
        onOptionSelect={handleChange}
        //value={store.schemaSelectedOption?.optionText ?? ""}
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
