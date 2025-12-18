"use client"

import Head from 'next/head';
import Footer from './Components/Footer';
import Recommender from './Components/Recommender';


export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <Head>
        <title>SHL AI Assessment Recommender</title>
        <meta name="description" content="Intelligent SHL assessment recommendations powered by AI" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <header className="bg-black">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-white">
              SHL Assessment Recommendation System
            </h1>
            <div className="flex items-center space-x-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-800 text-white">
                <a href="https://github.com/TechieLukesh/SHL">Github</a>
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <Recommender/>

      <Footer/>
    </div>
  );
}