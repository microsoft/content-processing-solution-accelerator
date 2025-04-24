import { TableRowId, TableRowData as RowStateBase, } from "@fluentui/react-components";
import { ListChildComponentProps } from "react-window";

export interface Item {
    fileName: { label: string; icon: JSX.Element };
    imported: { label: string };
    status: { label: string };
    processTime: { label: string };
    entityScore: { label: string };
    schemaScore: { label: string };
    processId: { label: string };
    lastModifiedBy: { label: string };
    file_mime_type: { label: string };
}

export interface TableRowData extends RowStateBase<Item> {
    onClick: (e: React.MouseEvent) => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
    selected: boolean;
    appearance: "brand" | "none";
}

export interface ReactWindowRenderFnProps extends ListChildComponentProps {
    data: TableRowData[];
    style: any;
    index: number;
}

export interface GridComponentProps { }
