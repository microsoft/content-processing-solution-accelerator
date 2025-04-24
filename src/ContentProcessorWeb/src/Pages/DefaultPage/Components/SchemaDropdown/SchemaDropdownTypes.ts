// types.ts
export interface OptionList {
    key: string; // Assuming `Id` is a string, change to `number` if needed
    value: string;
}

export interface SchemaItem {
    Id: string; // Adjust type if it's a number
    Description: string;
}

export interface StoreState {
    schemaData: SchemaItem[];
    schemaSelectedOption: { optionText: string } | null;
    schemaLoader: boolean;
    schemaError: string | null;
}
