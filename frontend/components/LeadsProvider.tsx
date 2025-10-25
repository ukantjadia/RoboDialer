"use client";
import React, { createContext, useContext, useState } from "react";

export type Lead = {
  id: number;
  lead_id?: string;
  company: string;
  website: string;
  industry: string;
  street: string;
  city: string;
  state: string;
  bbb_rating: string;
  business_phone: string;
};

type LeadsContextType = {
  leads: Lead[];
  setLeads: React.Dispatch<React.SetStateAction<Lead[]>>;
};

const LeadsContext = createContext<LeadsContextType | undefined>(undefined);

export const LeadsProvider = ({
  children,
  initialLeads = [],
}: {
  children: React.ReactNode;
  initialLeads?: Lead[];
}) => {
  const [leads, setLeads] = useState<Lead[]>(initialLeads || []);
  return (
    <LeadsContext.Provider value={{ leads, setLeads }}>
      {children}
    </LeadsContext.Provider>
  );
};

export const useLeads = () => {
  const context = useContext(LeadsContext);
  if (!context) throw new Error("useLeads must be used within a LeadsProvider");
  return context;
};
