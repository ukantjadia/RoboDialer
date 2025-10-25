import { useState } from "react";
import { CheckCircle, AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";

const STANDARD_FIELDS = [
	{ value: "revenue", label: "Revenue", description: "Total sales or income" },
	{ value: "date", label: "Date", description: "Transaction or record date" },
	{ value: "customer", label: "Customer", description: "Customer name or ID" },
	{ value: "category", label: "Category", description: "Product or expense category" },
	{ value: "cost", label: "Cost", description: "Cost of goods or services" },
	{ value: "ignore", label: "Ignore", description: "Do not analyze this column" },
];

export default function MappingStep({
	files,
	columnsByFile,
	onBack,
	onContinue,
}: {
	files: File[];
	columnsByFile: Record<string, string[]>;
	onBack: () => void;
	onContinue: (mappings: Record<string, Record<string, string>>) => void;
}) {
	const [mappings, setMappings] = useState<Record<string, Record<string, string>>>(
		Object.fromEntries(
			files.map((file) => [
				file.name,
				Object.fromEntries((columnsByFile[file.name] || []).map((col) => [col, "ignore"])),
			])
		)
	);

	const [confirmed, setConfirmed] = useState<Record<string, Record<string, boolean>>>(
		Object.fromEntries(
			files.map((file) => [
				file.name,
				Object.fromEntries((columnsByFile[file.name] || []).map((col) => [col, false])),
			])
		)
	);

	const [lastConfirmedValue, setLastConfirmedValue] = useState<Record<string, Record<string, string>>>(
		Object.fromEntries(
			files.map((file) => [
				file.name,
				Object.fromEntries((columnsByFile[file.name] || []).map((col) => [col, "ignore"])),
			])
		)
	);

	const [openFile, setOpenFile] = useState<string | null>(files[0]?.name || null);

	// If user changes the dropdown after confirming, revert confirmation
	const handleMappingChange = (fileName: string, col: string, value: string) => {
		setMappings((prev) => ({
			...prev,
			[fileName]: {
				...prev[fileName],
				[col]: value,
			},
		}));
		// If the value is changed after confirmation, revert confirmation
		if (confirmed[fileName]?.[col] && lastConfirmedValue[fileName]?.[col] !== value) {
			setConfirmed((prev) => ({
				...prev,
				[fileName]: { ...prev[fileName], [col]: false },
			}));
		}
	};

	const handleConfirm = (fileName: string, col: string) => {
		setConfirmed((prev) => ({
			...prev,
			[fileName]: { ...prev[fileName], [col]: true },
		}));
		setLastConfirmedValue((prev) => ({
			...prev,
			[fileName]: { ...prev[fileName], [col]: mappings[fileName][col] },
		}));
	};

	const allConfirmed = Object.values(confirmed).every((fileMap) =>
		Object.values(fileMap).every((val) => val)
	);

	return (
		<div className="flex flex-col items-center min-h-screen bg-dark-primary py-8">
			<div className="w-full max-w-4xl mx-auto">
				<h1 className="text-3xl font-bold text-center mb-6 text-white">
					Review Column Mapping
				</h1>
				<p className="text-gray-400 text-center mb-8">
					We've automatically mapped your columns to our standard fields. Please review and
					confirm.
				</p>
				<div className="space-y-4">
					{files.map((file) => (
						<div
							key={file.name}
							className="rounded-xl border border-dark-border bg-dark-secondary"
						>
							<button
								className="w-full flex items-center justify-between px-6 py-4 focus:outline-none"
								onClick={() =>
									setOpenFile(openFile === file.name ? null : file.name)
								}
								type="button"
							>
								<span className="text-blue-400 font-semibold text-lg flex items-center gap-2">
									{openFile === file.name ? (
										<ChevronDown className="w-5 h-5" />
									) : (
										<ChevronRight className="w-5 h-5" />
									)}
									{file.name}
								</span>
								<span className="text-xs text-gray-400">
									{
										Object.values(confirmed[file.name] || {})
											.filter(Boolean)
											.length
									}{" "}
									of {(columnsByFile[file.name] || []).length} confirmed
								</span>
							</button>
							{openFile === file.name && (
								<div className="px-6 pb-6">
									{(columnsByFile[file.name] || []).map((col, idx) => (
										<div
											key={col}
											className={`flex flex-col md:flex-row md:items-center gap-4 mb-4 p-4 rounded-lg border border-dark-border bg-dark-primary ${
												confirmed[file.name]?.[col]
													? "border-green-600 bg-green-950/30"
													: ""
											}`}
										>
											<div className="flex-1">
												<div className="text-gray-400 text-xs mb-1">
													Your Column
												</div>
												<div className="bg-dark-secondary rounded px-3 py-2 text-white font-mono">
													{col}
												</div>
											</div>
											<div className="flex-1">
												<div className="text-gray-400 text-xs mb-1">
													Maps to
												</div>
												<select
													className="w-full px-3 py-2 rounded border border-dark-border bg-dark-secondary text-white"
													value={mappings[file.name][col]}
													onChange={(e) =>
														handleMappingChange(file.name, col, e.target.value)
													}
												>
													{STANDARD_FIELDS.map((f) => (
														<option key={f.value} value={f.value}>
															{f.label}
														</option>
													))}
												</select>
												<div className="text-gray-500 text-xs mt-1">
													{
														STANDARD_FIELDS.find(
															(f) => f.value === mappings[file.name][col]
														)?.description
													}
												</div>
											</div>
											<div className="flex flex-col items-center gap-2">
												{!confirmed[file.name]?.[col] ? (
													<button
														className="px-4 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition"
														onClick={() => handleConfirm(file.name, col)}
														type="button"
													>
														Confirm
													</button>
												) : (
													<span className="flex items-center text-green-400 text-sm font-semibold">
														<CheckCircle className="w-4 h-4 mr-1" /> Confirmed
													</span>
												)}
											</div>
										</div>
									))}
								</div>
							)}
						</div>
					))}
				</div>
				<div className="bg-dark-primary border border-dark-border rounded-lg p-4 mb-6 mt-8">
					<div className="flex items-center text-yellow-500 mb-2">
						<AlertTriangle className="w-5 h-5 mr-2" />
						<span className="font-semibold">Review Tips</span>
					</div>
					<ul className="text-gray-300 text-sm list-disc list-inside pl-2">
						<li>Our AI detected these mappings with 85% confidence</li>
						<li>
							You can change any mapping using the dropdown menus before confirming
						</li>
						<li>Select "Ignore" for columns you don't want to analyze</li>
						<li>Click "Confirm" for each column to lock in your mapping</li>
						<li>Changing the mapping after confirming will require confirmation again</li>
						<li>Correct mappings ensure accurate insights in your dashboard</li>
					</ul>
				  </div>
				<div className="flex justify-between mt-6">
					<button
						className="px-6 py-2 rounded bg-gray-700 hover:bg-gray-600 text-white font-semibold transition"
						onClick={onBack}
					>
						Back to Upload
					</button>
					<button
						className={`px-6 py-2 rounded font-semibold transition ${
							allConfirmed
								? "bg-blue-600 hover:bg-blue-700 text-white"
								: "bg-gray-500 text-gray-300 cursor-not-allowed"
						}`}
						disabled={!allConfirmed}
						onClick={() => onContinue(mappings)}
					>
						Continue to Analysis Templates
					</button>
				</div>
			</div>
		</div>
	);
}