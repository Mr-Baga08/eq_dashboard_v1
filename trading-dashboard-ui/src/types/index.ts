// Trading related types
export interface Client {
    id: number;
    client_code: string;
    name: string;
    email: string;
    is_active: boolean;
    risk_profile: string;
  }
  
  export interface Token {
    id: number;
    token: string;
    symbol: string;
    name: string;
    exchange: string;
    segment: string;
  }
  
  export interface TradeConfig {
    token_id: string;
    symbol: string;
    exchange: string;
    order_type: string;
    transaction_type: string;
    product_type: string;
  }
  
  export interface ClientOrder {
    client_id: number;
    quantity: number;
    price?: number;
    remarks?: string;
  }
  
  export interface BatchOrderRequest {
    token_id: string;
    symbol: string;
    exchange: string;
    order_type: string;
    transaction_type: string;
    product_type: string;
    default_price?: number;
    client_orders: ClientOrder[];
    dry_run?: boolean;
  }
  
  export interface ApiResponse<T> {
    success: boolean;
    message: string;
    data: T;
  }