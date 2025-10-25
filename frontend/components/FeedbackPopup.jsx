import { useState } from "react";
import { MessageSquare } from "lucide-react";

export default function FeedbackPopup() {
  const [isOpen, setIsOpen] = useState(false);
  const togglePopup = () => setIsOpen(!isOpen);

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={togglePopup}
        className="fixed bottom-6 right-6 p-4 bg-gradient-to-r from-teal-400 to-blue-500 text-white rounded-full shadow-lg opacity-30 hover:opacity-100 transition-opacity duration-200"
        title="Send Feedback"
        >
        <MessageSquare className="w-6 h-6" />
    </button>

      {/* Popup Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-[#0d1117] text-white w-full max-w-lg p-6 rounded-xl shadow-lg relative">
            <button
              onClick={togglePopup}
              className="absolute top-3 right-3 text-gray-400 hover:text-white text-xl"
            >
              &times;
            </button>

            <h2 className="text-xl font-bold mb-4">Send us a message</h2>

            <form
            action="https://formsubmit.co/partners@capraecapital.com"
            method="POST"
            className="space-y-4"
            >
            {/* Hidden config for FormSubmit */}
            <input type="hidden" name="_captcha" value="false" />
            <input
                type="hidden"
                name="_next"
                value="https://yourdomain.com/thank-you"
            />

            <div className="flex gap-4">
                <div className="w-1/2">
                <label className="block text-sm font-medium mb-1" htmlFor="name">Name</label>
                <input
                    type="text"
                    name="name"
                    id="name"
                    required
                    placeholder="Your name"
                    className="w-full px-4 py-2 rounded-md bg-gray-800 text-white border border-gray-700 focus:outline-none"
                />
                </div>
                <div className="w-1/2">
                <label className="block text-sm font-medium mb-1" htmlFor="email">Email</label>
                <input
                    type="email"
                    name="email"
                    id="email"
                    required
                    placeholder="you@company.com"
                    className="w-full px-4 py-2 rounded-md bg-gray-800 text-white border border-gray-700 focus:outline-none"
                />
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium mb-1" htmlFor="subject">Subject</label>
                <input
                type="text"
                name="subject"
                id="subject"
                placeholder="Feedback or Report subject"
                className="w-full px-4 py-2 rounded-md bg-gray-800 text-white border border-gray-700 focus:outline-none"
                />
            </div>

            <div>
                <label className="block text-sm font-medium mb-1" htmlFor="message">Message</label>
                <textarea
                name="message"
                id="message"
                rows="4"
                required
                placeholder="Your message here..."
                className="w-full px-4 py-2 rounded-md bg-gray-800 text-white border border-gray-700 focus:outline-none"
                ></textarea>
            </div>

            <button
                type="submit"
                className="w-full bg-gradient-to-r from-teal-400 to-blue-500 py-2 rounded-md text-white font-semibold hover:opacity-90"
            >
                Send Message
            </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
